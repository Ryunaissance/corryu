---
description: "[Full Cycle] Multi-Agent Product Development Pipeline"
---
# 🌐 Multi-Agent Development Pipeline

This workflow coordinates the 5 specialized agents (PO, UX/UI, FE, BE, QA) to take a feature from a raw idea to a tested, deployable state.

## The 5-Step Agentic Cycle

When the user asks to **"Run the Multi-Agent Pipeline for feature X"**, you must seamlessly transition through the following personas in order. You may use the `task_boundary` tool to explicitly update the UI to show which Agent Mode you are currently in.

### Step 1: PO Agent (Planning)
- **Action**: Act as the PO. Create the PRD in `docs/prd/`. 
- **Wait**: Automatically proceed to Step 2 once the PRD is saved.

### Step 2: UX/UI Agent (Design)
- **Action**: Act as the Designer. Read the PRD. Create the UI Spec in `docs/design/`.
- **Wait**: Automatically proceed to Step 3.

### Step 3: Frontend Agent (Execution - UI)
- **Action**: Act as the FE Dev. Modify HTML/CSS/JS files to build the interface.

### Step 4: Backend Agent (Execution - Data)
- **Action**: Act as the BE Dev. Modify Python data scripts and create SQL migrations if required.
- **Wait**: Do not proceed to Step 5 if the user needs to manually run SQL migrations. If user action is required, stop and `notify_user`.

### Step 5: QA Agent (Verification)
- **Action**: Act as the QA. Write Playwright Scenarios in `tests/scenarios/`, generate `.spec.ts` files, and run tests via `npx playwright test`. Auto-heal any broken tests.

## Completion
Once Step 5 passes, present a final congratulatory report summarizing the contribution of each Agent!
