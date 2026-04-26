import streamlit as st
import pandas as pd
from src import db
from datetime import datetime


# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Manager Coaching Portal", layout="wide")
db.init_db()


# --- SIDEBAR: MANAGER LOGIN SIMULATION ---
st.sidebar.title("Login")
manager_id = st.sidebar.number_input("Enter Manager ID", min_value=1, value=1, step=1)
st.sidebar.info(f"Simulating logged in portal for Manager ID: {manager_id}")
# --- SIDEBAR: NOTIFICATION CENTER ---
st.sidebar.markdown("---")
st.sidebar.markdown("###  Notification Center")

notifications = db.get_active_lock_notifications(int(manager_id))

if not notifications:
    st.sidebar.markdown(
        """
        <div style="
            background-color: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            padding: 10px 12px;
            color: #166534;
            font-size: 13px;
        ">
            All clear — no active locks.
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        f"<p style='color:#991b1b; font-size:13px; margin:0 0 8px 0;'>"
        f"{len(notifications)} active lock(s) require attention.</p>",
        unsafe_allow_html=True,
    )

    for notif in notifications:
        lock_id, notif_agent_id, notif_module_id, lock_reason, locked_timestamp = notif

        # Format timestamp — trim seconds 
        try:
            from datetime import datetime
            ts = datetime.strptime(locked_timestamp, "%Y-%m-%d %H:%M:%S")
            ts_display = ts.strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_display = locked_timestamp

        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #fff1f2;
                border-left: 4px solid #e11d48;
                border-radius: 6px;
                padding: 10px 12px;
                margin-bottom: 8px;
                font-size: 13px;
                line-height: 1.6;
            ">
                <strong>Agent {notif_agent_id}</strong> is locked on 
                <strong>Module {notif_module_id}</strong><br>
                <span style="color:#6b7280;">Reason: {lock_reason}</span><br>
                <span style="color:#6b7280;">Time: {ts_display}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
# --- SIDEBAR: RESET BUTTON ---
st.sidebar.markdown("---")
st.sidebar.markdown("##### Demo Controls")

if st.sidebar.button("Reset Database (For Demo)", width='stretch'):
    st.session_state["confirm_reset"] = True

if st.session_state.get("confirm_reset", False):
    st.sidebar.warning("This will wipe all quiz results, locks, and interventions.")
    col_yes, col_no = st.sidebar.columns(2)

    if col_yes.button("Confirm", key="confirm_yes", width='stretch'):
        db.reset_db_to_demo()
        st.session_state["confirm_reset"] = False
        st.sidebar.success("Database reset to demo state.")
        st.rerun()

    if col_no.button("Cancel", key="confirm_no", width='stretch'):
        st.session_state["confirm_reset"] = False
        st.rerun()


# --- MAIN UI ---
st.title("Manager Coaching Intervention Portal")


# --- TABS ---
tab1, tab2 = st.tabs(["Team Learning Health Roster", "Enter Agent Quiz Result (For Demo)"], on_change='rerun')


# --- TAB 1: TEAM HEALTH ROSTER ---
with tab1:
    st.header("Team Learning Health Roster")
    msg = """Click one agent to inspect details.

**Status Info:**  
Healthy: Agent is learning normally.  
Warning: Agent has a 70 < rolling score < 80. (Total quizzes taken ≥ 3)  
Locked: Agent failed a certain module for 3 consecutive times, or has a rolling score < 70.
    """

    st.write(msg)

    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("Refresh", key="refresh_roster_btn", width="content"):
            st.rerun()

    if tab1.open:
        roster_query, roster_data = db.get_team_ovr_roster(manager_id)
        df = pd.DataFrame(roster_data, columns=["agent_id", "status"])
    else:
        df = pd.DataFrame(columns=["agent_id", "status"])

    if df.empty:
        st.warning("No direct reports found for this manager.")
    else:
        def color_status(val):
            if val == "Healthy":
                return "background-color: #d1fae5; color: #065f46;"
            elif val == "Warning":
                return "background-color: #fef3c7; color: #92400e;"
            elif val == "Locked":
                return "background-color: #fee2e2; color: #991b1b;"
            return ""

        df = df.reset_index(drop=True)
        styled_df = df.style.map(color_status, subset=["status"])

        event = st.dataframe(
            styled_df,
            width='stretch',
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="team_roster_table",
        )

        selected_rows = event["selection"]["rows"] # pyright: ignore[reportTypedDictNotRequiredAccess]

        st.markdown("---")

        if selected_rows:
            selected_idx = selected_rows[0]
            selected_agent = df.iloc[selected_idx]

            agent_id = int(selected_agent["agent_id"])
            status = selected_agent["status"]

            st.subheader(f"Agent {agent_id} Details")
            st.caption(f"Status: **{status}**")

            if status in ["Healthy", "Warning"]:
                quiz_query, quiz_data = db.get_agent_quiz_results(agent_id)
                quiz_df = pd.DataFrame(
                    quiz_data,
                    columns=[
                        "module_id",
                        "state",
                        "score",
                        "is_pass",
                        "interaction_speed",
                        "finished_timestamp",
                    ],
                )
                if quiz_df.empty:
                    st.info("No quiz results found for this agent.")
                else:
                    st.dataframe(quiz_df, width='stretch', hide_index=True)

            elif status == "Locked":
                lock_query, lock_data = db.get_agent_module_locks(agent_id)
                lock_df = pd.DataFrame(
                    lock_data,
                    columns=["lock_id", "module_id", "lock_reason", "failing_question", "ai_feedback"],
                )
                if lock_df.empty:
                    st.info("No active lock found for this agent.")
                else:
                    st.caption("Active locks — click **Log Intervention & Unlock** to log a coaching intervention.")

                    header = st.columns([1, 2, 3, 3, 2])
                    header[0].markdown("**Module ID**")
                    header[1].markdown("**Lock Reason**")
                    header[2].markdown("**Failing Question**")
                    header[3].markdown("**AI Feedback**")
                    header[4].markdown("**Action**")

                    st.markdown(
                        "<hr style='margin: 4px 0 8px 0; border-color: #e5e7eb;'>",
                        unsafe_allow_html=True,
                    )

                    for _, lock_row in lock_df.iterrows():
                        lock_id = int(lock_row["lock_id"])
                        mod_id  = int(lock_row["module_id"])

                        row_cols = st.columns([1, 2, 3, 3, 2])

                        with row_cols[0]:
                            st.markdown(
                                f"<div style='padding: 8px 4px; border: 1px solid #e5e7eb; "
                                f"border-radius: 6px; text-align: center; background: #f9fafb;'>"
                                f"<strong>{mod_id}</strong></div>",
                                unsafe_allow_html=True,
                            )

                        with row_cols[1]:
                            color = "#fef3c7"
                            text_color = "#92400e"
                            st.markdown(
                                f"<div style='padding: 8px 6px; border: 1px solid #e5e7eb; "
                                f"border-radius: 6px; background: {color}; color: {text_color}; "
                                f"font-size: 13px;'>{lock_row['lock_reason']}</div>",
                                unsafe_allow_html=True,
                            )

                        with row_cols[2]:
                            st.markdown(
                                f"<div style='padding: 8px 6px; border: 1px solid #e5e7eb; "
                                f"border-radius: 6px; background: #f9fafb; font-size: 13px;'>"
                                f"{lock_row['failing_question']}</div>",
                                unsafe_allow_html=True,
                            )

                        with row_cols[3]:
                            st.markdown(
                                f"<div style='padding: 8px 6px; border: 1px solid #e5e7eb; "
                                f"border-radius: 6px; background: #f9fafb; font-size: 13px;'>"
                                f"{lock_row['ai_feedback']}</div>",
                                unsafe_allow_html=True,
                            )

                        with row_cols[4]:
                            if st.button(
                                "Log Intervention & Unlock",
                                key=f"unlock_btn_{lock_id}",
                                type="secondary",
                                width='stretch',
                            ):
                                st.session_state[f"unlock_modal_{lock_id}"] = True

                        st.markdown(
                            "<hr style='margin: 4px 0; border-color: #f3f4f6;'>",
                            unsafe_allow_html=True,
                        )

                        if st.session_state.get(f"unlock_modal_{lock_id}", False):
                            with st.form(key=f"intervention_form_{lock_id}"):
                                st.subheader(f"Log Intervention — Module {mod_id}")
                                st.markdown(
                                    "Please describe what was discussed in the 1-on-1 session."
                                )

                                notes = st.text_area(
                                    "Manager Intervention Log (Minimum 10 words)",
                                    placeholder="e.g. We reviewed the failing questions together and agreed on a study plan...",
                                    value="Asked if there is any problem at work, discussed about the failing question, and agreed on a study plan.",
                                    height=120,
                                    key=f"notes_{lock_id}",
                                )

                                submitted = st.form_submit_button(
                                    "Digital Signature",
                                    width='stretch',
                                )

                                if submitted:
                                    word_count = len(notes.strip().split())

                                    if word_count < 10:
                                        st.error(
                                            f"Your log has only {word_count} word(s). "
                                            "Please write at least 10 words before confirming."
                                        )
                                    else:
                                        db.log_intervention_and_unlock(
                                            lock_id=lock_id,
                                            manager_id=int(manager_id),
                                            manager_notes_text=notes.strip(),
                                            agent_id=agent_id,
                                            module_id=mod_id,
                                        )
                                        st.session_state[f"unlock_modal_{lock_id}"] = False
                                        st.success(
                                            f"Intervention logged. Module {mod_id} unlocked."
                                        )
                                        st.rerun()

                if st.button("Module Overview", key=f"overview_btn_{agent_id}"):
                    overview_query, overview_data = db.get_agent_quiz_results(agent_id)
                    overview_df = pd.DataFrame(
                        overview_data,
                        columns=[
                            "module_id",
                            "state",
                            "score",
                            "is_pass",
                            "interaction_speed",
                            "finished_timestamp",
                        ],
                    )
                    if overview_df.empty:
                        st.info("No module overview data found.")
                    else:
                        st.dataframe(overview_df, width='stretch', hide_index=True)

        else:
            st.info("Select one row from the roster above to see agent details.")

# --- TAB 2: Enter Agent Quiz Result (For Demo) ---
with tab2:
    st.header("Enter Agent Quiz Result (For Demo)")

    test_agent_id = st.number_input("Agent ID", min_value=2, max_value=11, value=2, step=1, key="test_agent_id")
    test_module_id = st.number_input("Module ID", min_value=1, max_value=5, value=1, step=1, key="test_module_id")
    test_score = st.number_input("Score", min_value=0, max_value=100, step=1, key="test_score")
    test_speed = st.number_input("Interaction Speed", min_value=0, value=1, step=1, key="test_speed")
    test_is_pass_str = st.selectbox("Is Pass", ["YES", "NO"], key="test_is_pass")
    if test_is_pass_str == "YES":
        test_is_pass = 1
    else:
        test_is_pass = 0

    if st.button("Insert Test Quiz Result"):
        try:
            if hasattr(db, "insert_quiz_result"):
                db.insert_quiz_result(
                    agent_id=test_agent_id,
                    module_id=test_module_id,
                    score=test_score,
                    is_pass=test_is_pass,
                    interaction_speed=test_speed,
                    finished_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                st.success("Test quiz result inserted successfully.")
            else:
                st.warning("db.insert_quiz_result() is not implemented yet in src/db.py.")
        except Exception as e:
            st.error(f"Failed to insert test quiz result: {e}")

    if st.button("Refresh Page"):
        st.rerun()