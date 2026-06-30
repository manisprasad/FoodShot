---
name: create-skill
description: A meta-skill that scaffolds and generates new AI agent skills in the .agents/skills directory.
---

# Instructions for the `create-skill` meta-skill

This is a meta-skill used to automate the creation of new skills for the agent. Whenever the user wants to teach the AI a new recurring workflow, this skill handles the boilerplate.

## Steps the AI must follow:
1. **Clarify Requirements:** If the user hasn't provided the name or purpose of the new skill, ask them (e.g., "What should the new skill do?").
2. **Format:** Determine a concise `kebab-case` folder name for the skill.
3. **Scaffold:** Create a new file at `.agents/skills/<skill-name>/SKILL.md`.
4. **Draft Content:** Write the `SKILL.md` content strictly in **English** (as it is the best practice for LLM instructions). 
   - It MUST include YAML frontmatter with `name:` and `description:`.
   - It MUST include a clear `# Instructions` section detailing the step-by-step actions the AI should take when the skill is invoked.
5. **Success message:** Notify the user that the skill has been created and is immediately ready to be used in any new conversation.
