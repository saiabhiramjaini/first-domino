---
paths:
  - ".claude/skills/**"
  - "**/SKILL.md"
---

# Writing Claude skills

Project skills live in `.claude/skills/<name>/SKILL.md`.

- **Description.** It is routing text and loads in every session. Say what the skill does and the kinds of request it serves as a few intent categories, then name the nearby requests it must not take (`Do NOT use for ...`). Write in the third person.
- **Body.** State the goal, the defaults a model cannot guess, the constraints with their reasons, and how to check the result. Give exact commands only where one sequence is the only safe one.
- **Output.** Pin a template only where a reader needs a fixed shape, and say what to leave out.
- **Examples.** Add one only where it pins a format that prose cannot, and label it illustrative.
- If a skill does not fire, sharpen its intent categories. If it fires and does the wrong thing, make the vague instruction specific, with its reason.
