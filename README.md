# Manager Coaching Intervention Portal

A small Streamlit demo app that simulates how a **team manager** can monitor agent learning condition, get **lock notifications**, and **log coaching interventions** before digitally unlocking access again.

The backend is a lightweight **SQLite trigger engine** that decides when an agent is:
- Healthy
- Warning
- Locked (pending coaching)

and records a full audit trail of each unlock.

---

## Features

### 1. Team Learning Health Roster

- Manager logs in via sidebar. For demo, login feature is currently via selecting (`Manager ID`).
- Main roster shows all direct reports and their current **learning health status**:
  - **Healthy** – learning normally.
  - **Warning** – 7‑day rolling average score (across all modules) is between 70 and 80, with at least 3 quiz attempts.
  - **Locked** – either:
    - agent failed the **same module** 3 times consecutively, or  
    - 7‑day rolling average score (across all modules) is below 70, with at least 3 quiz attempts.
- Click an agent row to open **Agent Details**:
  - For **Healthy / Warning**: shows quiz history joined with `ModuleLearningProgress.state`.
  - For **Locked**: shows active module locks plus unlock controls.

### 2. Lock / Unlock Workflow

- When a lock condition is met for `(agent_id, module_id)`, the engine:
  - Updates `ModuleLearningProgress.state → 'Locked_Pending_Coaching'`.
  - Inserts a row into `ModuleStateLocks` with:
    - `lock_reason` = `"Failing 3X"` or `"Rolling Score < 70"`.
    - `locked_timestamp`.
  - Updates `AgentLearningStatus.status` to `"Locked"` if any module is locked.

- In the **Agent Details** panel for a locked agent:
  - Each active lock row displays:

    | Module ID | Lock Reason | Failing Question | AI Feedback | Action |

  - The **Log Intervention & Unlock** button opens a form:
    - Text area: *“Manager Intervention Log (Minimum 10 words)”*.
    - Button: **Digital Signature**.
  - On submit (with ≥10 words):
    - Inserts a row into `CoachingInterventions`:
      - `intervention_id` (sequential),
      - `lock_id`,
      - `manager_id`,
      - `manager_notes_text`,
      - `unlocked_timestamp`.
    - Updates `ModuleLearningProgress.state → 'Active'`.
    - Updates `ModuleStateLocks.is_locked → 0`.
    - Recomputes `AgentLearningStatus.status`:
      - `"Locked"` if any other modules remain locked.
      - `"Healthy"` otherwise.

### 3. Notification Center (Sidebar)

- For the currently selected manager, shows a **card-based list** of active locks:

  > Agent {agent_id} is locked on Module {module_id}  
  > Reason: {lock_reason}  
  > Time: {locked_timestamp}

- If there are no active locks, shows a green “All clear — no active locks” message.
- Updates automatically whenever quiz results trigger new locks or unlocks.

### 4. Rolling Score Engine

The background engine runs after every quiz result insert (`insert_quiz_result` → `run_background_check`):

- **Scope**:
  - **Failing 3X** logic is per `(agent_id, module_id)`.
  - **Rolling average** logic is **across all modules** for that `agent_id`.
- **Inputs**:
  - All quiz results in the last **7 days** where `is_pass = 0`.
  - Only triggers rolling logic when there are **at least 3** such attempts.
- **Cooldown**:
  - After a coaching intervention unlock, there is a **3‑day cooldown per module**:
    - During cooldown, that module cannot lock again.
    - However, overall rolling averages can still generate **Warning** at the agent level.
- **Decisions**:
  - `ModuleLearningProgress.state`:
    - `"Finished"` if **any quiz** for that module has `is_pass = 1`.
    - `"Active"` during cooldown or if rules do not trigger a lock.
    - `"Locked_Pending_Coaching"` for:
      - 3+ consecutive fails on that specific module, or
      - 7‑day cross‑module rolling average `< 70` and not in cooldown.
  - `AgentLearningStatus.status`:
    - `"Locked"` if **any** module is `"Locked_Pending_Coaching"`.
    - `"Warning"` if cross‑module 7‑day average `< 80` (with ≥3 fails) and no lock.
    - `"Healthy"` otherwise.

---

## Project Structure

```text
Manager_Coaching_Portal/
├── .vscode/              # Editor settings (optional)
├── data/
│   └── portal.db         # SQLite database
├── src/
│   ├── __init__.py
│   └── db.py             # DB schema, seed data, trigger logic, helpers
└── main.py               # Streamlit app
```

---

## Core Database Tables

- **TeamStructures**
  - Org mapping: `mapping_id`, `agent_id`, `manager_id`, `branch_code`, `effective_date`.

- **QuizResults**
  - Raw quiz attempts: `result_id`, `agent_id`, `module_id`, `score`, `is_pass`, `interaction_speed`, `finished_timestamp`.

- **ModuleLearningProgress**
  - Module state per agent: `(agent_id, module_id)` → `state` (`Not Start Yet`, `Active`, `Finished`, `Locked_Pending_Coaching`).

- **AgentLearningStatus**
  - Overall health per agent: `agent_id` → `status` (`Healthy`, `Warning`, `Locked`).

- **ModuleStateLocks**
  - Lock records per module: `lock_id`, `agent_id`, `module_id`, `lock_reason`, `locked_timestamp`, `is_locked`, `failing_question`, `ai_feedback`.

- **CoachingInterventions**
  - Coaching audit trail: `intervention_id`, `lock_id`, `manager_id`, `manager_notes_text`, `unlocked_timestamp`.

---