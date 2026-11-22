import { describe, expect, it } from "vitest";

import { checkDemoLogin, demoSubject } from "./demo-login";

const LOGIN = { email: "judge@firstdomino.dev", password: "dominoes-fall" };

describe("checkDemoLogin", () => {
  it("signs in with the right email and password", () => {
    expect(checkDemoLogin(LOGIN, " Judge@FirstDomino.dev ", "dominoes-fall")).toEqual({
      id: demoSubject(LOGIN.email),
      email: LOGIN.email,
      name: "Test reviewer",
    });
  });

  it("refuses a wrong password, a wrong email or missing fields", () => {
    expect(checkDemoLogin(LOGIN, LOGIN.email, "dominoes-fal")).toBeNull();
    expect(checkDemoLogin(LOGIN, "other@firstdomino.dev", LOGIN.password)).toBeNull();
    expect(checkDemoLogin(LOGIN, undefined, LOGIN.password)).toBeNull();
    expect(checkDemoLogin(LOGIN, LOGIN.email, 42)).toBeNull();
  });
});
