import { cn, formatCost, formatMs, formatTokens } from "@/lib/utils";

test("formatMs shows milliseconds below one second and seconds above", () => {
  expect(formatMs(0)).toBe("0 ms");
  expect(formatMs(568.03)).toBe("568 ms");
  expect(formatMs(999.6)).toBe("1.00 s");
  expect(formatMs(1686.55)).toBe("1.69 s");
});

test("cn merges tailwind classes", () => {
  expect(cn("p-2", "p-4")).toBe("p-4");
});

test("formatCost keeps two significant digits and only rounds true dust", () => {
  expect(formatCost(0)).toBe("$0");
  expect(formatCost(0.0004)).toBe("$0.0004");
  expect(formatCost(0.00007)).toBe("$0.00007");
  expect(formatCost(0.000004)).toBe("<$0.00001");
  expect(formatCost(1.234)).toBe("$1.2");
});

test("formatTokens", () => {
  expect(formatTokens(850)).toBe("850 tokens");
  expect(formatTokens(1900)).toBe("1.9k tokens");
});
