import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Dropzone } from "@/components/app/Dropzone";
import { api, ApiError } from "@/lib/api";
import type { IngestStage } from "@/lib/types";

const MB = 1024 * 1024;

function setup() {
  const onUploaded = vi.fn();
  render(<Dropzone onUploaded={onUploaded} pollMs={5} />);
  const input = screen.getByLabelText(/choose a file/i, { selector: "input" }) as HTMLInputElement;
  return { onUploaded, input };
}

afterEach(() => vi.restoreAllMocks());

const status = (s: IngestStage, error: string | null = null) => ({ document_id: "d1", status: s, error, pages: null });

function processing(id = "d1", filename = "cv.pdf") {
  return vi.spyOn(api, "uploadDocument").mockResolvedValue({ document_id: id, filename, status: "processing" });
}

test("rejects other file types before uploading", async () => {
  const upload = vi.spyOn(api, "uploadDocument");
  const { input } = setup();
  await userEvent.upload(input, new File(["x"], "pic.png"), { applyAccept: false });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Only PDF, Word, PowerPoint, HTML or TXT files can be uploaded.",
  );
  expect(upload).not.toHaveBeenCalled();
});

test("rejects files over 10 MB before uploading", async () => {
  const upload = vi.spyOn(api, "uploadDocument");
  const { input } = setup();
  const big = new File(["x"], "big.pdf");
  Object.defineProperty(big, "size", { value: 10 * MB + 1 });
  await userEvent.upload(input, big);
  expect(await screen.findByRole("alert")).toHaveTextContent("File is larger than 10 MB");
  expect(upload).not.toHaveBeenCalled();
});

test("uploads and reports the document", async () => {
  processing();
  vi.spyOn(api, "getIngestStatus").mockResolvedValue(status("ready"));
  const { input, onUploaded } = setup();
  await userEvent.upload(input, new File(["%PDF"], "cv.pdf"));
  await vi.waitFor(() => expect(onUploaded).toHaveBeenCalledWith({ documentId: "d1", fileName: "cv.pdf" }));
});

test("server error is shown and Try again re-sends the same file", async () => {
  const upload = vi
    .spyOn(api, "uploadDocument")
    .mockRejectedValueOnce(new ApiError(400, "This PDF appears to be image-based (scanned)..."))
    .mockResolvedValueOnce({ document_id: "d2", filename: "scan.pdf", status: "processing" });
  vi.spyOn(api, "getIngestStatus").mockResolvedValue({ ...status("ready"), document_id: "d2" });
  const { input, onUploaded } = setup();
  const file = new File(["%PDF"], "scan.pdf");
  await userEvent.upload(input, file);

  expect(await screen.findByRole("alert")).toHaveTextContent("image-based (scanned)");
  await userEvent.click(screen.getByRole("button", { name: "Try again" }));
  await vi.waitFor(() => expect(onUploaded).toHaveBeenCalledWith({ documentId: "d2", fileName: "scan.pdf" }));
  expect(upload).toHaveBeenNthCalledWith(2, file);
});

test("keyboard: Enter on the drop zone opens the file picker", async () => {
  const { input } = setup();
  const click = vi.spyOn(input, "click");
  screen.getByRole("button", { name: /choose a file/i }).focus();
  await userEvent.keyboard("{Enter}");
  expect(click).toHaveBeenCalled();
});

test("clicking the drop zone opens the file picker exactly once", async () => {
  const { input } = setup();
  const click = vi.spyOn(input, "click");
  await userEvent.click(screen.getByRole("button", { name: /choose a file/i }));
  expect(click).toHaveBeenCalledTimes(1);
});

test("privacy notice names the providers and does not promise a fixed retention", () => {
  // Retention is TRACE_RETENTION_DAYS on the server (0 = forever); the UI can't know it
  setup();
  const notice = screen.getByText(/TypeSafe/);
  expect(notice).toHaveTextContent("OpenRouter");
  expect(notice).toHaveTextContent("for a retention period set by the operator");
  expect(notice).not.toHaveTextContent(/\d+ days/);
});

test("accepts Word, PowerPoint and HTML files", async () => {
  processing();
  vi.spyOn(api, "getIngestStatus").mockResolvedValue(status("ready"));
  const { input } = setup();
  expect(input.accept).toBe(".pdf,.txt,.docx,.pptx,.html");
  expect(screen.getByText("PDF, Word, PowerPoint, HTML or TXT · max 10 MB")).toBeInTheDocument();
  for (const name of ["cv.docx", "deck.pptx", "page.html"]) {
    await userEvent.upload(input, new File(["x"], name));
  }
  await vi.waitFor(() => expect(api.uploadDocument).toHaveBeenCalledTimes(3));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("shows the real stage while processing, then opens the document", async () => {
  processing();
  let release!: () => void;
  const gate = new Promise<void>((r) => (release = r));
  const stages = [status("queued"), status("parsing"), status("chunking")];
  vi.spyOn(api, "getIngestStatus").mockImplementation(async () => {
    const next = stages.shift();
    if (next) return next;
    await gate;
    return status("ready");
  });
  const { input, onUploaded } = setup();
  await userEvent.upload(input, new File(["%PDF"], "cv.pdf"));
  expect(await screen.findByText("Waiting for another upload to finish…")).toBeInTheDocument();
  expect(await screen.findByText("Reading pages (OCR where needed)…")).toBeInTheDocument();
  expect(await screen.findByText("Splitting into chunks…")).toBeInTheDocument();
  expect(onUploaded).not.toHaveBeenCalled();
  release();
  await vi.waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(1));
  expect(onUploaded).toHaveBeenCalledWith({ documentId: "d1", fileName: "cv.pdf" });
});

test("a failed ingestion shows its error with Try again", async () => {
  processing();
  vi.spyOn(api, "getIngestStatus").mockResolvedValue(
    status("failed", "Couldn't read this file. It may be corrupt or password-protected."),
  );
  const { input, onUploaded } = setup();
  await userEvent.upload(input, new File(["x"], "bad.pdf"));
  expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't read this file.");
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  expect(onUploaded).not.toHaveBeenCalled();
});

test("one failed status check keeps polling", async () => {
  processing();
  vi.spyOn(api, "getIngestStatus").mockRejectedValueOnce(new Error("network")).mockResolvedValue(status("ready"));
  const { input, onUploaded } = setup();
  await userEvent.upload(input, new File(["%PDF"], "cv.pdf"));
  await vi.waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(1));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("five failed status checks in a row give up with an error", async () => {
  processing();
  vi.spyOn(api, "getIngestStatus").mockRejectedValue(new Error("network"));
  const { input, onUploaded } = setup();
  await userEvent.upload(input, new File(["%PDF"], "cv.pdf"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Lost contact with the server while processing. Please try again.",
  );
  expect(api.getIngestStatus).toHaveBeenCalledTimes(5);
  expect(onUploaded).not.toHaveBeenCalled();
});
