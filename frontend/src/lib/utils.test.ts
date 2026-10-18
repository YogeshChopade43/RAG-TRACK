import { cn, formatMs } from "@/lib/utils";

test("formatMs shows milliseconds below one second and seconds above", () => {
  expect(formatMs(0)).toBe("0 ms");
  expect(formatMs(568.03)).toBe("568 ms");
  expect(formatMs(999.6)).toBe("1.00 s");
  expect(formatMs(1686.55)).toBe("1.69 s");
});

test("cn merges tailwind classes", () => {
  expect(cn("p-2", "p-4")).toBe("p-4");
});
