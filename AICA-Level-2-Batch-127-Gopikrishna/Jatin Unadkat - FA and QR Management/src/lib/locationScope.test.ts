import { describe, it, expect } from "vitest";
import { isInScope, locationScopeWhereClause } from "./locationScope";

describe("isInScope", () => {
  const roots = ["Mumbai"];

  it("matches the root location itself", () => {
    expect(isInScope("Mumbai", roots)).toBe(true);
  });

  it("matches any descendant under the root", () => {
    expect(isInScope("Mumbai / Head Office / Finance / Room 204", roots)).toBe(true);
  });

  it("does not match a sibling location outside the assigned scope", () => {
    expect(isInScope("Delhi", roots)).toBe(false);
  });

  it("does not match a location whose name merely starts with the same characters", () => {
    // "Mumbai Suburb" should not be treated as inside "Mumbai" scope by a naive
    // string prefix check that forgets the separator boundary.
    expect(isInScope("Mumbai Suburb Office", roots)).toBe(false);
  });

  it("supports multiple assigned roots", () => {
    const multi = ["Mumbai", "Pune"];
    expect(isInScope("Pune / Warehouse", multi)).toBe(true);
    expect(isInScope("Delhi", multi)).toBe(false);
  });
});

describe("locationScopeWhereClause", () => {
  it("produces a clause that can never match anything when there are no assigned roots", () => {
    const clause = locationScopeWhereClause([]);
    expect(clause).toEqual({ fullPath: "__no_scope__" });
  });

  it("produces an OR of startsWith filters for each root", () => {
    const clause = locationScopeWhereClause(["Mumbai", "Pune"]);
    expect(clause).toEqual({
      OR: [{ fullPath: { startsWith: "Mumbai" } }, { fullPath: { startsWith: "Pune" } }],
    });
  });
});
