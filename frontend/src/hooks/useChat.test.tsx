import { act, renderHook, waitFor } from "@testing-library/react";
import { useChat } from "@/hooks/useChat";
import { api, ApiError } from "@/lib/api";
import type { QueryResponse } from "@/lib/types";

const answer = (text: string): QueryResponse => ({
  trace_id: "t1",
  question: "q",
  answer: text,
  sources: [{ file_name: "cv.pdf", page_number: 1 }],
});

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

afterEach(() => vi.restoreAllMocks());

test("ask shows a pending answer, then the answer with sources and trace id", async () => {
  const d = deferred<QueryResponse>();
  vi.spyOn(api, "query").mockReturnValue(d.promise);
  const { result } = renderHook(() => useChat("docA"));

  act(() => result.current.ask("Who is Jane?"));
  expect(result.current.pending).toBe(true);
  expect(result.current.messages.map((m) => [m.role, m.status])).toEqual([
    ["user", "done"],
    ["assistant", "pending"],
  ]);

  await act(async () => d.resolve(answer("Jane is a data engineer.")));
  const last = result.current.messages[1];
  expect(last).toMatchObject({
    status: "done",
    content: "Jane is a data engineer.",
    traceId: "t1",
    sources: [{ file_name: "cv.pdf", page_number: 1 }],
  });
  expect(result.current.pending).toBe(false);
});

test("double submit sends one request", () => {
  const query = vi.spyOn(api, "query").mockReturnValue(new Promise(() => {}));
  const { result } = renderHook(() => useChat("docA"));
  act(() => {
    result.current.ask("first");
    result.current.ask("second");
  });
  expect(query).toHaveBeenCalledTimes(1);
});

test("a late answer for a previous document is dropped", async () => {
  const d = deferred<QueryResponse>();
  vi.spyOn(api, "query").mockReturnValue(d.promise);
  const { result, rerender } = renderHook(({ doc }) => useChat(doc), { initialProps: { doc: "docA" } });

  act(() => result.current.ask("question about A"));
  rerender({ doc: "docB" });
  expect(result.current.messages).toEqual([]);

  await act(async () => d.resolve(answer("answer about A")));
  expect(result.current.messages).toEqual([]);
  expect(result.current.pending).toBe(false);
});

test("a failure shows the error and Retry re-asks the same question", async () => {
  const query = vi
    .spyOn(api, "query")
    .mockRejectedValueOnce(new ApiError(500, "Query processing failed"))
    .mockResolvedValueOnce(answer("Recovered."));
  const { result } = renderHook(() => useChat("docA"));

  await act(async () => result.current.ask("What is her role?"));
  const failed = result.current.messages[1];
  expect(failed).toMatchObject({ status: "error", error: "Query processing failed" });

  await act(async () => result.current.retry(failed.id));
  await waitFor(() => expect(result.current.messages[1]).toMatchObject({ status: "done", content: "Recovered." }));
  expect(query).toHaveBeenNthCalledWith(2, "docA", "What is her role?");
  expect(result.current.messages).toHaveLength(2);
});
