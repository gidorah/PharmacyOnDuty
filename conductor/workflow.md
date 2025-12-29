# Project Workflow

## Guiding Principles

1. **The Plan is the Source of Truth:** All work must be tracked in `plan.md`
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation
3. **Test-Driven Development:** Write unit tests before implementing functionality
4. **High Code Coverage:** Aim for >80% code coverage for all modules
5. **User Experience First:** Every decision should prioritize user experience
6. **Non-Interactive & CI-Aware:** Prefer non-interactive commands. Use `CI=true` for watch-mode tools (tests, linters) to ensure single execution.

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow

1. **Select Task:** Choose the next available task from `plan.md` in sequential order

2. **Mark In Progress:** Before beginning work, edit `plan.md` and change the task from `[ ]` to `[~]`

3. **Write Failing Tests (Red Phase):**
   - Create a new test file for the feature or bug fix.
   - Write one or more unit tests that clearly define the expected behavior and acceptance criteria for the task.
   - **CRITICAL:** Run the tests and confirm that they fail as expected. This is the "Red" phase of TDD. Do not proceed until you have failing tests.

4. **Implement to Pass Tests (Green Phase):**
   - Write the minimum amount of application code necessary to make the failing tests pass.
   - Run the test suite again and confirm that all tests now pass. This is the "Green" phase.

5. **Refactor (Optional but Recommended):**
   - With the safety of passing tests, refactor the implementation code and the test code to improve clarity, remove duplication, and enhance performance without changing the external behavior.
   - Rerun tests to ensure they still pass after refactoring.

6. **Verify Coverage:** Run coverage reports using the project's chosen tools. For example, in a Python project, this might look like:
   ```bash
   pytest --cov=app --cov-report=html
   ```
   Target: >80% coverage for new code. The specific tools and commands will vary by language and framework.

7. **Document Deviations:** If implementation differs from tech stack:
   - **STOP** implementation
   - Update `tech-stack.md` with new design
   - Add dated note explaining the change
   - Resume implementation

8. **Mark Task Complete:**
   - **Action:** Read `plan.md`.
   - **Action:** Find the line for the completed task and update its status from `[~]` to `[x]`.
   - **Action:** Write the updated content back to `plan.md`.
   - **Note:** Do *not* commit changes yet. Commits are performed at the end of the Phase.

### Phase Completion Verification and Checkpointing Protocol

**Trigger:** This protocol is executed immediately after a task is completed that also concludes a phase in `plan.md`.

1.  **Announce Protocol Start:** Inform the user that the phase is complete and the verification and checkpointing protocol has begun.

2.  **Ensure Test Coverage for Phase Changes:**
    -   **Step 2.1: Determine Phase Scope:** To identify the files changed in this phase, you must first find the starting point. Read `plan.md` to find the Git commit SHA of the *previous* phase's checkpoint. If no previous checkpoint exists, the scope is all changes since the first commit.
    -   **Step 2.2: List Changed Files:** Execute `git diff --name-only <previous_checkpoint_sha> HEAD` to get a precise list of all files modified during this phase.
    -   **Step 2.3: Verify and Create Tests:** For each file in the list:
        -   **CRITICAL:** First, check its extension. Exclude non-code files (e.g., `.json`, `.md`, `.yaml`).
        -   For each remaining code file, verify a corresponding test file exists.
        -   If a test file is missing, you **must** create one. Before writing the test, **first, analyze other test files in the repository to determine the correct naming convention and testing style.** The new tests **must** validate the functionality described in this phase's tasks (`plan.md`).

3.  **Execute Automated Tests with Proactive Debugging:**
    -   Before execution, you **must** announce the exact shell command you will use to run the tests.
    -   **Example Announcement:** "I will now run the automated test suite to verify the phase. **Command:** `CI=true npm test`"
    -   Execute the announced command.
    -   If tests fail, you **must** inform the user and begin debugging. You may attempt to propose a fix a **maximum of two times**. If the tests still fail after your second proposed fix, you **must stop**, report the persistent failure, and ask the user for guidance.

4.  **Propose a Detailed, Actionable Manual Verification Plan:**
    -   **CRITICAL:** To generate the plan, first analyze `product.md`, `product-guidelines.md`, and `plan.md` to determine the user-facing goals of the completed phase.
    -   You **must** generate a step-by-step plan that walks the user through the verification process, including any necessary commands and specific, expected outcomes.
    -   The plan you present to the user **must** follow this format:

        **For a Frontend Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Start the development server with the command:** `npm run dev`
        2.  **Open your browser to:** `http://localhost:3000`
        3.  **Confirm that you see:** The new user profile page, with the user's name and email displayed correctly.
        ```

        **For a Backend Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Ensure the server is running.**
        2.  **Execute the following command in your terminal:** `curl -X POST http://localhost:8080/api/v1/users -d '{"name": "test"}'`
        3.  **Confirm that you receive:** A JSON response with a status of `201 Created`.
        ```

5.  **Await Explicit User Feedback:**
    -   After presenting the detailed plan, ask the user for confirmation: "**Does this meet your expectations? Please confirm with yes or provide feedback on what needs to be changed.**"
    -   **PAUSE** and await the user's response. Do not proceed without an explicit yes or confirmation.

6.  **Create Checkpoint Commit:**
    -   **Action:** Stage all application code changes, test files, and documentation (including `readme.md`) modified during the phase.
    -   **Action:** Perform the commit with a message summarizing the phase (e.g., `feat(phase): Complete Phase X: <Short Description>`).
    -   **Action:** Record the commit hash (`git log -1 --format="%H"`).

7.  **Attach Auditable Verification Report using Git Notes:**
    -   **Step 7.1: Draft Note Content:** Create a comprehensive report including:
        -   List of all tasks completed in this phase.
        -   The automated test command used.
        -   The manual verification steps and results.
        -   The explicit user confirmation.
    -   **Step 7.2: Attach Note:** Use `git notes add -m "<report content>" <commit_hash>`.

8.  **Get and Record Phase Checkpoint SHA:**
    -   **Step 8.1: Update Plan:** Read `plan.md`, find the heading for the completed phase, and append the checkpoint SHA in the format `[checkpoint: <sha>]`. Also update the status of the verification task to `[x]`.
    -   **Step 8.2: Write Plan:** Save the updated `plan.md`.

9. **Finalize Phase:**
    - **Action:** Stage and commit the updated `plan.md` with the message `conductor(plan): Mark phase '<PHASE NAME>' as complete`.

10.  **Announce Completion:** Inform the user that the phase is complete and the checkpoint has been created, with the detailed verification report attached as a git note.

### Quality Gates

Before marking any task complete, verify:

- [ ] All tests pass
- [ ] Code coverage meets requirements (>80%)
- [ ] Code follows project's code style guidelines (as defined in `code_styleguides/`)
- [ ] All public functions/methods are documented (e.g., docstrings, JSDoc, GoDoc)
- [ ] Type safety is enforced (e.g., type hints, TypeScript types, Go types)
- [ ] No linting or static analysis errors (using the project's configured tools)
- [ ] Works correctly on mobile (if applicable)
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities introduced

## Development Commands

**AI AGENT INSTRUCTION: This section should be adapted to the project's specific language, framework, and build tools.**

### Setup
```bash
# Example: Commands to set up the development environment (e.g., install dependencies, configure database)
# e.g., for a Node.js project: npm install
# e.g., for a Go project: go mod tidy
```

### Daily Development
```bash
# Example: Commands for common daily tasks (e.g., start dev server, run tests, lint, format)
# e.g., for a Node.js project: npm run dev, npm test, npm run lint
# e.g., for a Go project: go run main.go, go test ./..., go fmt ./...
```

### Before Committing
```bash
# Example: Commands to run all pre-commit checks (e.g., format, lint, type check, run tests)
# e.g., for a Node.js project: npm run check
# e.g., for a Go project: make check (if a Makefile exists)
```

## Testing Requirements

### Unit Testing
- Every module must have corresponding tests.
- Use appropriate test setup/teardown mechanisms (e.g., fixtures, beforeEach/afterEach).
- Mock external dependencies.
- Test both success and failure cases.

### Integration Testing
- Test complete user flows
- Verify database transactions
- Test authentication and authorization
- Check form submissions

### Mobile Testing
- Test on actual iPhone when possible
- Use Safari developer tools
- Test touch interactions
- Verify responsive layouts
- Check performance on 3G/4G

## Code Review Process

### Self-Review Checklist
Before requesting review:

1. **Functionality**
   - Feature works as specified
   - Edge cases handled
   - Error messages are user-friendly

2. **Code Quality**
   - Follows style guide
   - DRY principle applied
   - Clear variable/function names
   - Appropriate comments

3. **Testing**
   - Unit tests comprehensive
   - Integration tests pass
   - Coverage adequate (>80%)

4. **Security**
   - No hardcoded secrets
   - Input validation present
   - SQL injection prevented
   - XSS protection in place

5. **Performance**
   - Database queries optimized
   - Images optimized
   - Caching implemented where needed

6. **Mobile Experience**
   - Touch targets adequate (44x44px)
   - Text readable without zooming
   - Performance acceptable on mobile
   - Interactions feel native

## Commit Guidelines

### Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Maintenance tasks

### Examples
```bash
git commit -m "feat(auth): Add remember me functionality"
git commit -m "fix(posts): Correct excerpt generation for short posts"
git commit -m "test(comments): Add tests for emoji reaction limits"
git commit -m "style(mobile): Improve button touch targets"
```

## Definition of Done

A task is complete when:

1. All code implemented to specification
2. Unit tests written and passing
3. Code coverage meets project requirements
4. Documentation complete (including `readme.md` if applicable)
5. Code passes all configured linting and static analysis checks
6. Works beautifully on mobile (if applicable)
7. Task marked as `[x]` in `plan.md`

## Emergency Procedures

### Critical Bug in Production
1. Create hotfix branch from main
2. Write failing test for bug
3. Implement minimal fix
4. Test thoroughly including mobile
5. Deploy immediately
6. Document in plan.md

### Data Loss
1. Stop all write operations
2. Restore from latest backup
3. Verify data integrity
4. Document incident
5. Update backup procedures

### Security Breach
1. Rotate all secrets immediately
2. Review access logs
3. Patch vulnerability
4. Notify affected users (if any)
5. Document and update security procedures

## Deployment Workflow

### Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Coverage >80%
- [ ] No linting errors
- [ ] Mobile testing complete
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Backup created

### Deployment Steps
1. Merge feature branch to main
2. Tag release with version
3. Push to deployment service
4. Run database migrations
5. Verify deployment
6. Test critical paths
7. Monitor for errors

### Post-Deployment
1. Monitor analytics
2. Check error logs
3. Gather user feedback
4. Plan next iteration

## Continuous Improvement

- Review workflow weekly
- Update based on pain points
- Document lessons learned
- Optimize for user happiness
- Keep things simple and maintainable

---

## 6.0 SYNCHRONIZE PROJECT DOCUMENTATION
**PROTOCOL: Update project-level documentation based on the completed track.**

1.  **Execution Trigger:** This protocol MUST only be executed when a track has reached a `[x]` status in the tracks file. DO NOT execute this protocol for any other track status changes.

2.  **Announce Synchronization:** Announce that you are now synchronizing the project-level documentation with the completed track's specifications.

3.  **Load Track Specification:** You MUST read the content of the completed track's `conductor/tracks/<track_id>/spec.md` file into your context.

4.  **Load Project Documents:** You MUST read the contents of the following project-level documents into your context:
    -   `conductor/product.md`
    -   `conductor/product-guidelines.md`
    -   `conductor/tech-stack.md`
    -   `readme.md`

5.  **Analyze and Update:**
    a.  **Analyze `spec.md`:** Carefully analyze the `spec.md` to identify any new features, changes in functionality, or updates to the technology stack.
    b.  **Update `conductor/product.md`:**
        i. **Condition for Update:** Based on your analysis, you MUST determine if the completed feature or bug fix significantly impacts the description of the product itself.
        ii. **Propose and Confirm Changes:** If an update is needed, generate the proposed changes. Then, present them to the user for confirmation:
            > "Based on the completed track, I propose the following updates to `product.md`:"
            > ```diff
            > [Proposed changes here, ideally in a diff format]
            > ```
            > "Do you approve these changes? (yes/no)"
        iii. **Action:** Only after receiving explicit user confirmation, perform the file edits to update the `conductor/product.md` file. Keep a record of whether this file was changed.
    c.  **Update `conductor/tech-stack.md`:**
        i. **Condition for Update:** Similarly, you MUST determine if significant changes in the technology stack are detected as a result of the completed track.
        ii. **Propose and Confirm Changes:** If an update is needed, generate the proposed changes. Then, present them to the user for confirmation:
            > "Based on the completed track, I propose the following updates to `tech-stack.md`:"
            > ```diff
            > [Proposed changes here, ideally in a diff format]
            > ```
            > "Do you approve these changes? (yes/no)"
        iii. **Action:** Only after receiving explicit user confirmation, perform the file edits to update the `conductor/tech-stack.md` file. Keep a record of whether this file was changed.
    d.  **Update `readme.md`:**
        i. **Condition for Update:** Analyze if the changes affect the project overview, features, installation steps, configuration, or technology list in `readme.md`.
        ii. **Propose and Confirm Changes:** If an update is needed, generate the proposed changes. Then, present them to the user for confirmation:
            > "Based on the completed track, I propose the following updates to `readme.md`:"
            > ```diff
            > [Proposed changes here, ideally in a diff format]
            > ```
            > "Do you approve these changes? (yes/no)"
        iii. **Action:** Only after receiving explicit user confirmation, perform the file edits to update the `readme.md` file. Keep a record of whether this file was changed.
    e. **Update `conductor/product-guidelines.md` (Strictly Controlled):**
        i. **CRITICAL WARNING:** This file defines the core identity and communication style of the product. It should be modified with extreme caution and ONLY in cases of significant strategic shifts, such as a product rebrand or a fundamental change in user engagement philosophy. Routine feature updates or bug fixes should NOT trigger changes to this file.
        ii. **Condition for Update:** You may ONLY propose an update to this file if the track's `spec.md` explicitly describes a change that directly impacts branding, voice, tone, or other core product guidelines.
        iii. **Propose and Confirm Changes:** If the conditions are met, you MUST generate the proposed changes and present them to the user with a clear warning:
            > "WARNING: The completed track suggests a change to the core product guidelines. This is an unusual step. Please review carefully:"
            > ```diff
            > [Proposed changes here, ideally in a diff format]
            > ```
            > "Do you approve these critical changes to `product-guidelines.md`? (yes/no)"
        iv. **Action:** Only after receiving explicit user confirmation, perform the file edits. Keep a record of whether this file was changed.

6.  **Final Report:** Announce the completion of the synchronization process and provide a summary of the actions taken.
    - **Construct the Message:** Based on the records of which files were changed, construct a summary message.
    - **Example (if product.md was changed, but others were not):**
        > "Documentation synchronization is complete.
        > - **Changes made to `product.md`:** The user-facing description of the product was updated to include the new feature.
        > - **No changes needed for `tech-stack.md`:** The technology stack was not affected.
        > - **No changes needed for `readme.md`:** The public documentation was not affected.
        > - **No changes needed for `product-guidelines.md`:** Core product guidelines remain unchanged."
    - **Example (if no files were changed):**
        > "Documentation synchronization is complete. No updates were necessary for `product.md`, `tech-stack.md`, `readme.md`, or `product-guidelines.md` based on the completed track."

---

## 7.0 TRACK CLEANUP
**PROTOCOL: Offer to archive or delete the completed track.**

1.  **Execution Trigger:** This protocol MUST only be executed after the current track has been successfully implemented and the `SYNCHRONIZE PROJECT DOCUMENTATION` step is complete.

2.  **Ask for User Choice:** You MUST prompt the user with the available options for the completed track.
    > "Track '<track_description>' is now complete. What would you like to do?
    > A.  **Archive:** Move the track's folder to `conductor/archive/` and remove it from the tracks file.
    > B.  **Delete:** Permanently delete the track's folder and remove it from the tracks file.
    > C.  **Skip:** Do nothing and leave it in the tracks file.
    > Please enter the number of your choice (A, B, or C)."

3.  **Handle User Response:**
    *   **If user chooses "A" (Archive):**
        i.   **Create Archive Directory:** Check for the existence of `conductor/archive/`. If it does not exist, create it.
        ii.  **Archive Track Folder:** Move the track's folder from `conductor/tracks/<track_id>` to `conductor/archive/<track_id>`.
        iii. **Remove from Tracks File:** Read the content of `conductor/tracks.md`, remove the entire section for the completed track (the part that starts with `---` and contains the track description), and write the modified content back to the file.
        iv.  **Announce Success:** Announce: "Track '<track_description>' has been successfully archived."
    *   **If user chooses "B" (Delete):**
        i. **CRITICAL WARNING:** Before proceeding, you MUST ask for a final confirmation due to the irreversible nature of the action.
            > "WARNING: This will permanently delete the track folder and all its contents. This action cannot be undone. Are you sure you want to proceed? (yes/no)"
        ii. **Handle Confirmation:**
            - **If 'yes'**:
                a. **Delete Track Folder:** Permanently delete the track's folder from `conductor/tracks/<track_id>`.
                b. **Remove from Tracks File:** Read the content of `conductor/tracks.md`, remove the entire section for the completed track, and write the modified content back to the file.
                c. **Announce Success:** Announce: "Track '<track_description>' has been permanently deleted."
            - **If 'no' (or anything else)**:
                a. **Announce Cancellation:** Announce: "Deletion cancelled. The track has not been changed."
    *   **If user chooses "C" (Skip) or provides any other input:**
        *   Announce: "Okay, the completed track will remain in your tracks file for now."
