import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "portal.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. TeamStructures (The Org Chart) 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "TeamStructures" (
                "mapping_id"	INTEGER NOT NULL UNIQUE,
                "agent_id"	INTEGER NOT NULL UNIQUE,
                "manager_id"	INTEGER,
                "branch_code"	TEXT NOT NULL,
                "effective_date"	TEXT NOT NULL,
                PRIMARY KEY("mapping_id")
            )
        ''')

        # 2. ModuleStateLocks (The Access Control)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "ModuleStateLocks" (
                "lock_id"          INTEGER NOT NULL UNIQUE,
                "agent_id"         INTEGER NOT NULL,
                "module_id"        INTEGER NOT NULL,
                "lock_reason"      TEXT NOT NULL,
                "locked_timestamp" TEXT NOT NULL,
                "is_locked"        INTEGER NOT NULL,
                "failing_question" TEXT NOT NULL,
                "ai_feedback"      TEXT,
                PRIMARY KEY("lock_id"),
                FOREIGN KEY("agent_id", "module_id")
                    REFERENCES "ModuleLearningProgress"("agent_id", "module_id")
            )
        ''')

        # 3. CoachingInterventions (The Audit Trail)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "CoachingInterventions" (
                "intervention_id"	INTEGER NOT NULL UNIQUE,
                "lock_id"	INTEGER NOT NULL,
                "manager_id"	INTEGER NOT NULL,
                "manager_notes_text"	TEXT NOT NULL,
                "unlocked_timestamp"	TEXT,
                PRIMARY KEY("intervention_id"),
                FOREIGN KEY("lock_id") REFERENCES "ModuleStateLocks"("lock_id"),
                FOREIGN KEY("manager_id") REFERENCES "TeamStructures"("agent_id")
            )
        ''')

        # 4. QuizResults (To support the Trigger Engine) [cite: 17-18]
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "QuizResults" (
                "result_id"	INTEGER NOT NULL UNIQUE,
                "agent_id"	INTEGER NOT NULL,
                "module_id"	INTEGER NOT NULL,
                "score"	INTEGER,
                "is_pass"	INTEGER,
                "interaction_speed"	INTEGER,
                "finished_timestamp"	TEXT,
                PRIMARY KEY("result_id"),
                FOREIGN KEY("agent_id") REFERENCES "TeamStructures"("agent_id")
            )
        ''')

        # 5. AgentLearningStatus (Color Marker) 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "AgentLearningStatus" (
                "agent_id"	INTEGER NOT NULL UNIQUE,
                "status"	TEXT NOT NULL,
                PRIMARY KEY("agent_id"),
                FOREIGN KEY("agent_id") REFERENCES "TeamStructures"("agent_id")
                )
        ''')

        # 6. ModuleLearningProgress (Record State)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "ModuleLearningProgress" (
                "agent_id"	INTEGER NOT NULL,
                "module_id"	INTEGER NOT NULL,
                "state"	TEXT NOT NULL DEFAULT 'Not Start Yet',
                PRIMARY KEY("agent_id","module_id"),
                FOREIGN KEY("agent_id") REFERENCES "TeamStructures"("agent_id")
                )
        ''')
        conn.commit()

def entry_db():
    # Insert Values 
    with get_connection() as conn:
        cursor = conn.cursor()
        # 1. TeamStructures
        cursor.executemany(
            """
            INSERT INTO TeamStructures (mapping_id, agent_id, manager_id, branch_code, effective_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, 1, None, 'BR001', '2026-04-17'),  # manager
                (2, 2, 1, 'BR001', '2026-04-17'),
                (3, 3, 1, 'BR001', '2026-04-17'),
                (4, 4, 1, 'BR001', '2026-04-17'),
                (5, 5, 1, 'BR001', '2026-04-17'),
                (6, 6, 1, 'BR001', '2026-04-17'),
                (7, 7, 1, 'BR001', '2026-04-17'),
                (8, 8, 1, 'BR001', '2026-04-17'),
                (9, 9, 1, 'BR001', '2026-04-17'),
                (10, 10, 1, 'BR001', '2026-04-17'),
                (11, 11, 1, 'BR001', '2026-04-17'),
            ],
        )

        # 2. AgentLearningStatus
        cursor.executemany(
            """
            INSERT INTO AgentLearningStatus (agent_id, status)
            VALUES (?, ?)
            """,
            [
                (2, 'Healthy'),
                (3, 'Healthy'),
                (4, 'Healthy'),
                (5, 'Healthy'),
                (6, 'Healthy'),
                (7, 'Healthy'),
                (8, 'Healthy'),
                (9, 'Healthy'),
                (10, 'Healthy'),
                (11, 'Healthy'),
            ],
        )

        # 3. ModuleLearningProgress
        rows = []
        for module_id in range(1, 6):
            for agent_id in range(2, 12):
                rows.append((module_id, agent_id, 'Not Start Yet'))


        cursor.executemany(
        """
        INSERT INTO ModuleLearningProgress (module_id, agent_id, state)
        VALUES (?, ?, ?)
        """,
        rows,
        )

        conn.commit()
        conn.close()

def get_team_ovr_roster(manager_id): 

    query = """
        SELECT 
            t.agent_id,
            als.status
        FROM TeamStructures t
        LEFT JOIN AgentLearningStatus als ON t.agent_id = als.agent_id
        WHERE t.manager_id = ?
    """
    
    with get_connection() as conn:
        rows =  conn.execute(query, (manager_id,)).fetchall()
        
    return query, rows    

def get_agent_quiz_results(agent_id):
    query = """
        SELECT 
            qr.module_id,
            mlp.state,
            qr.score,
            qr.is_pass,
            qr.interaction_speed,
            qr.finished_timestamp
        FROM QuizResults qr
        LEFT JOIN ModuleLearningProgress mlp 
            ON qr.agent_id = mlp.agent_id
            AND qr.module_id = mlp.module_id
        WHERE qr.agent_id = ?
        ORDER BY qr.finished_timestamp DESC
    """
    
    with get_connection() as conn:
        rows = conn.execute(query, (agent_id,)).fetchall()
        
    return query, rows


def get_agent_module_locks(agent_id):
    query = """
        SELECT 
            msl.lock_id,
            msl.module_id,
            msl.lock_reason,
            msl.failing_question,
            msl.ai_feedback
        FROM ModuleStateLocks msl
        WHERE msl.agent_id = ?
          AND msl.is_locked = 1
    """
    
    with get_connection() as conn:
        rows = conn.execute(query, (agent_id,)).fetchall()
        
    return query, rows


def insert_quiz_result(
    agent_id: int,
    module_id: int,
    score: float,
    is_pass: int,
    interaction_speed: float,
    finished_timestamp: str,
):
    """
    Insert one row into QuizResults.
    result_id is auto-assigned as MAX(result_id) + 1.
    After insert, triggers run_background_check for (agent_id, module_id).
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(result_id), 0) + 1 FROM QuizResults"
        ).fetchone()
        next_result_id = row[0]

        conn.execute(
            """
            INSERT INTO QuizResults
                (result_id, agent_id, module_id, score, is_pass,
                 interaction_speed, finished_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_result_id,
                agent_id,
                module_id,
                score,
                is_pass,
                interaction_speed,
                finished_timestamp,
            ),
        )
        conn.commit()

    run_background_check(agent_id, module_id, finished_timestamp)

def run_background_check(agent_id: int, module_id: int, finished_timestamp):

    with get_connection() as conn:

        module_attempts = conn.execute(
            """
            SELECT score, is_pass, finished_timestamp
            FROM QuizResults
            WHERE agent_id = ? AND module_id = ?
            ORDER BY finished_timestamp DESC
            """,
            (agent_id, module_id),
        ).fetchall()

        if not module_attempts:
            return

        total_attempts = len(module_attempts)
        any_pass = any(row[1] == 1 for row in module_attempts)

        now = datetime.now()
        cutoff_7d = now - timedelta(days=7)

        all_recent_scores = conn.execute(
            """
            SELECT score
            FROM QuizResults
            WHERE agent_id = ?
              AND finished_timestamp >= ?
              AND is_pass = 0
            ORDER BY finished_timestamp DESC
            """,
            (agent_id, cutoff_7d.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchall()

        recent_scores = [row[0] for row in all_recent_scores]
        rolling_avg = (
            sum(recent_scores) / len(recent_scores)
            if len(recent_scores) >= 3
            else None  # Not enough data — skip rolling avg checks
        )

        # Check 3-day cooldown after last unlock for this module 
        cutoff_3d = now - timedelta(days=3)

        recent_unlock = conn.execute(
            """
            SELECT ci.unlocked_timestamp
            FROM CoachingInterventions ci
            JOIN ModuleStateLocks msl ON ci.lock_id = msl.lock_id
            WHERE msl.agent_id = ? AND msl.module_id = ?
            ORDER BY ci.unlocked_timestamp DESC
            LIMIT 1
            """,
            (agent_id, module_id),
        ).fetchone()

        in_cooldown = (
            recent_unlock is not None
            and datetime.strptime(recent_unlock[0], "%Y-%m-%d %H:%M:%S") >= cutoff_3d
        )

        lock_reason = None

        if any_pass:
            new_mlp_state = "Finished"

        elif in_cooldown:
            new_mlp_state = "Active"

        else:
            if total_attempts > 2:
                # Failing 3X: scoped to this specific module
                new_mlp_state = "Locked_Pending_Coaching"
                lock_reason = "Failing 3X"
            elif rolling_avg is not None and rolling_avg < 70:
                # Cross-module rolling avg too low
                new_mlp_state = "Locked_Pending_Coaching"
                lock_reason = "Rolling Score < 70"
            else:
                new_mlp_state = "Active"

        existing_mlp = conn.execute(
            """
            SELECT state FROM ModuleLearningProgress
            WHERE agent_id = ? AND module_id = ?
            """,
            (agent_id, module_id),
        ).fetchone()

        prev_mlp_state = existing_mlp[0] if existing_mlp else None

        if existing_mlp:
            conn.execute(
                """
                UPDATE ModuleLearningProgress
                SET state = ?
                WHERE agent_id = ? AND module_id = ?
                """,
                (new_mlp_state, agent_id, module_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO ModuleLearningProgress (agent_id, module_id, state)
                VALUES (?, ?, ?)
                """,
                (agent_id, module_id, new_mlp_state),
            )

        if (
            new_mlp_state == "Locked_Pending_Coaching"
            and prev_mlp_state != "Locked_Pending_Coaching"
        ):
            next_lock_id_row = conn.execute(
                "SELECT COALESCE(MAX(lock_id), 0) + 1 FROM ModuleStateLocks"
            ).fetchone()
            next_lock_id = next_lock_id_row[0]

            conn.execute(
                """
                INSERT INTO ModuleStateLocks
                    (lock_id, agent_id, module_id, lock_reason,
                     locked_timestamp, is_locked, failing_question, ai_feedback)
                VALUES (?, ?, ?, ?, ?, 1, 'Failing Question', 'AI Feedback')
                """,
                (
                    next_lock_id, agent_id, module_id, lock_reason,
                    finished_timestamp,
                ),
            )

        any_locked_module = conn.execute(
            """
            SELECT 1 FROM ModuleLearningProgress
            WHERE agent_id = ? AND state = 'Locked_Pending_Coaching'
            LIMIT 1
            """,
            (agent_id,),
        ).fetchone()

        if any_locked_module:
            new_als_status = "Locked"
        elif rolling_avg is not None and rolling_avg < 80:
            new_als_status = "Warning"
        else:
            new_als_status = "Healthy"

        existing_als = conn.execute(
            "SELECT status FROM AgentLearningStatus WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()

        if existing_als:
            conn.execute(
                "UPDATE AgentLearningStatus SET status = ? WHERE agent_id = ?",
                (new_als_status, agent_id),
            )
        else:
            conn.execute(
                "INSERT INTO AgentLearningStatus (agent_id, status) VALUES (?, ?)",
                (agent_id, new_als_status),
            )

        conn.commit()

def log_intervention_and_unlock(
    lock_id: int,
    manager_id: int,
    manager_notes_text: str,
    agent_id: int,
    module_id: int,
):
    """
    1. Insert a CoachingInterventions row
    2. Update ModuleLearningProgress.state -> 'Active'
    3. Update ModuleStateLocks.is_locked -> 0
    """

    with get_connection() as conn:
        next_id_row = conn.execute(
            "SELECT COALESCE(MAX(intervention_id), 0) + 1 FROM CoachingInterventions"
        ).fetchone()
        next_intervention_id = next_id_row[0]

        unlocked_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            """
            INSERT INTO CoachingInterventions
                (intervention_id, lock_id, manager_id,
                 manager_notes_text, unlocked_timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                next_intervention_id,
                lock_id,
                manager_id,
                manager_notes_text,
                unlocked_timestamp,
            ),
        )

        conn.execute(
            """
            UPDATE ModuleLearningProgress
            SET state = 'Active'
            WHERE agent_id = ? AND module_id = ?
            """,
            (agent_id, module_id),
        )

        conn.execute(
            """
            UPDATE ModuleStateLocks
            SET is_locked = 0
            WHERE lock_id = ?
            """,
            (lock_id,),
        )

        any_still_locked = conn.execute(
            """
            SELECT 1 FROM ModuleLearningProgress
            WHERE agent_id = ? AND state = 'Locked_Pending_Coaching'
            LIMIT 1
            """,
            (agent_id,),
        ).fetchone()

        new_als_status = "Locked" if any_still_locked else "Healthy"

        conn.execute(
            """
            UPDATE AgentLearningStatus
            SET status = ?
            WHERE agent_id = ?
            """,
            (new_als_status, agent_id),
        )

        conn.commit()

def reset_db_to_demo():
    """
    Resets the database to the initial demo state.
    Delete order strictly follows FK dependency chain (children before parents):
      CoachingInterventions → ModuleStateLocks → QuizResults
      → AgentLearningStatus → ModuleLearningProgress → TeamStructures
    """
    with get_connection() as conn:
        cursor = conn.cursor()


        cursor.execute("PRAGMA foreign_keys = ON")


        cursor.execute("DELETE FROM CoachingInterventions")  # refs ModuleStateLocks, TeamStructures
        cursor.execute("DELETE FROM ModuleStateLocks")       # refs ModuleLearningProgress
        cursor.execute("DELETE FROM QuizResults")            # refs TeamStructures
        cursor.execute("DELETE FROM AgentLearningStatus")    # refs TeamStructures
        cursor.execute("DELETE FROM ModuleLearningProgress") # refs TeamStructures
        cursor.execute("DELETE FROM TeamStructures")         # root parent — deleted last

        cursor.executemany(
            """
            INSERT INTO TeamStructures (mapping_id, agent_id, manager_id, branch_code, effective_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1,  1,  None, 'BR001', '2026-04-17'),
                (2,  2,  1,   'BR001', '2026-04-17'),
                (3,  3,  1,   'BR001', '2026-04-17'),
                (4,  4,  1,   'BR001', '2026-04-17'),
                (5,  5,  1,   'BR001', '2026-04-17'),
                (6,  6,  1,   'BR001', '2026-04-17'),
                (7,  7,  1,   'BR001', '2026-04-17'),
                (8,  8,  1,   'BR001', '2026-04-17'),
                (9,  9,  1,   'BR001', '2026-04-17'),
                (10, 10, 1,   'BR001', '2026-04-17'),
                (11, 11, 1,   'BR001', '2026-04-17'),
            ],
        )

        cursor.executemany(
            "INSERT INTO AgentLearningStatus (agent_id, status) VALUES (?, ?)",
            [(agent_id, 'Healthy') for agent_id in range(2, 12)],
        )

        cursor.executemany(
            "INSERT INTO ModuleLearningProgress (module_id, agent_id, state) VALUES (?, ?, ?)",
            [
                (module_id, agent_id, 'Not Start Yet')
                for module_id in range(1, 6)
                for agent_id in range(2, 12)
            ],
        )

        # QuizResults, ModuleStateLocks, CoachingInterventions stay empty

        conn.commit()

def get_active_lock_notifications(manager_id: int):
    """
    Returns all active locks for agents under this manager,
    ordered by most recent first.
    """
    query = """
        SELECT 
            msl.lock_id,
            msl.agent_id,
            msl.module_id,
            msl.lock_reason,
            msl.locked_timestamp
        FROM ModuleStateLocks msl
        JOIN TeamStructures t ON t.agent_id = msl.agent_id
        WHERE t.manager_id = ?
          AND msl.is_locked = 1
        ORDER BY msl.locked_timestamp DESC
    """
    with get_connection() as conn:
        rows = conn.execute(query, (manager_id,)).fetchall()
    return rows