import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Dropzone } from "@/components/app/Dropzone";
import { api, ApiError } from "@/lib/api";

const MB = 1024 * 1024;

function setup() {
  const onUploaded = vi.fn();
  render(<Dropzone onUploaded={onUploaded} />);
  const input = screen.getByLabelText(/choose a file/i, { selector: "input" }) as HTMLInputElement;
  return { onUploaded, input };
}

afterEach(() => vi.restoreAllMocks());

test("rejects other file types before uploading", async () => {
  const upload = vi.spyOn(api, "uploadDocument");
  const { input } = setup();
  await userEvent.upload(input, new File(["x"], "notes.docx"), { applyAccept: false });
  expect(await screen.findByRole("alert")).toHaveTextContent("Only PDF or TXT files");
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
  vi.spyOn(api, "uploadDocument").mockResolvedValue({
    document_id: "d1",
    filename: "cv.pdf",
    status: "completed",
  });
  const { input, onUploaded } = setup();
  await userEvent.upload(input, new File(["%PDF"], "cv.pdf"));
  await vi.waitFor(() => expect(onUploaded).toHaveBeenCalledWith({ documentId: "d1", fileName: "cv.pdf" }));
});

test("server error is shown and Try again re-sends the same file", async () => {
  const upload = vi
    .spyOn(api, "uploadDocument")
    .mockRejectedValueOnce(new ApiError(400, "This PDF appears to be image-based (scanned)..."))
    .mockResolvedValueOnce({ document_id: "d2", filename: "scan.pdf", status: "completed" });
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
