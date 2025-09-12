import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../Auth/auth.jsx";
import "./Dashboard.css";

/** Replace mock data with API later */
const GOAL = { title: "Land FAANG SWE Role", deadline: "Aug 15, 2025" };
const WEEKLY_TARGET_HOURS = 7; 

const INITIAL_TASKS = [
  { id: "t1", label: "LeetCode: 2 Medium DP problems", done: false },
  { id: "t2", label: "System Design: caching + CDNs (45m)", done: true },
  { id: "t3", label: "Project: implement auth flow (1h)", done: false },
  { id: "t4", label: "Networking: reach out to 2 alums", done: false },
];

const MILESTONES = [
  { when: "Week 4", what: "Finish arrays/strings module" },
  { when: "Week 8", what: "Mock interview #1" },
  { when: "Week 12", what: "Capstone project polish" },
];

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState(INITIAL_TASKS);

  const weeklyHours = 3.5;
  const weeklyPct = Math.min(100, Math.round((weeklyHours / WEEKLY_TARGET_HOURS) * 100));

  const checkedCount = tasks.filter(t => t.done).length;
  const tasksPct = Math.round((checkedCount / tasks.length) * 100);
  const streakDays = 5;

  const todayFocus = useMemo(
    () => tasks.find(t => !t.done)?.label ?? "You’re all caught up 🎉",
    [tasks]
  );

  function toggleTask(id) {
    setTasks(prev => prev.map(t => (t.id === id ? { ...t, done: !t.done } : t)));
  }

  return (
    <div className="cc">
      {/* Topbar */}
      <header className="cc__topbar">
        <div className="brand">
          <div className="brand__logo">◆</div>
          <div className="brand__name">CareerCoach</div>
        </div>

        <div className="top-actions">
          <div className="search">
            <input className="search__input" placeholder="Search…" />
          </div>
          <div className="user">
            <div className="user__avatar">
              {(user?.name?.[0] || user?.email?.[0] || "U").toUpperCase()}
            </div>
            <div className="user__meta">
              <div className="user__name">{user?.name || "User"}</div>
              <div className="user__email">{user?.email}</div>
            </div>
            <button onClick={logout} className="btn btn--ghost">Log out</button>
          </div>
        </div>
      </header>

        {/*Layout: 3 columns */}
      <div className="cc__grid">
        {/* Sidebar */}
        <aside className="side">
          <nav className="nav">
            <NavItem label="Dashboard" active />
            <NavItem label="Study Plan" to="/dashboard/plan" />
            <NavItem label="Progress" to="/dashboard/progress" />
            <NavItem label="Focus Timer" to="/dashboard/focus" />
            <NavItem label="Settings" to="/dashboard/settings" />
          </nav>
        </aside>

        {/* Main */}
        <main className="main">
          {/* Hero: Goal + CTA */}
          <section className="hero">
            <div className="hero__copy">
              <div className="eyebrow">Your Goal</div>
              <h1 className="hero__title">{GOAL.title}</h1>
              <p className="hero__meta">
                Deadline: <b>{GOAL.deadline}</b>
              </p>
              <Link to="/dashboard/plan" className="btn btn--light hero__cta">
                View Study Plan →
              </Link>

            </div>
            <div className="hero__meter">
              <div className="meter__label">Weekly Target</div>
              <Ring percent={weeklyPct} />
            </div>
          </section>

          {/* This Week tasks */}
          <section className="card">
            <div className="card__head">
              <h2 className="card__title">This Week</h2>
              <div className="card__meta">
                Hours: <b>{weeklyHours.toFixed(1)}</b> / {WEEKLY_TARGET_HOURS}
              </div>
            </div>

            <Progress percent={weeklyPct} />

            <div className="tasks">
              {tasks.map(t => (
                <button
                  key={t.id}
                  onClick={() => toggleTask(t.id)}
                  className={`task ${t.done ? "task--done" : ""}`}
                >
                  <input type="checkbox" readOnly checked={t.done} />
                  <span className="task__label">{t.label}</span>
                </button>
              ))}
            </div>

            <div className="card__foot">
              Tasks completed: <b>{checkedCount}</b> / {tasks.length} ({tasksPct}%)
            </div>
          </section>

          {/* Milestones & Focus */}
          <section className="grid2">
            <div className="card">
              <h3 className="card__title">Upcoming Milestones</h3>
              <ul className="milestones">
                {MILESTONES.map((m, i) => (
                  <li key={i} className="milestone">
                    <span className="milestone__what">{m.what}</span>
                    <span className="milestone__when">{m.when}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="card">
              <h3 className="card__title">Today’s Focus</h3>
              <p className="focus__text">{todayFocus}</p>
              <button className="btn btn--primary btn--full">Mark Done</button>
              <div className="divider" />
              <div className="tip">
                <div className="tip__title">Coaching Tip</div>
                <p className="tip__body">
                  Show up daily. 60 solid minutes today &gt; 0 perfect minutes tomorrow.
                </p>
              </div>
            </div>
          </section>
        </main>

        {/* Right rail */}
        <aside className="rail">
          <section className="card">
            <h3 className="card__title">Next Up</h3>
            <div className="next">
                {tasks.filter(t => !t.done).slice(0, 3).map((t, i) => (
                <div key={t.id} className="next__row">
                    <img className="next__thumb" src={`https://placehold.co/80x80?text=${i+1}`} alt="" />
                    <span className="next__label">{t.label}</span>
                    <span className="next__time">~25m</span>
                    <button className="chip" onClick={() => toggleTask(t.id)}>Start</button>
                </div>
                ))}
            </div>
          </section>

          <section className="card">
            <h3 className="card__title">This Week Summary</h3>
            <div className="split">
              <div className="muted">Tasks</div>
              <div className="strong">{checkedCount}/{tasks.length}</div>
            </div>
            <Progress percent={weeklyPct} />

            <div className="streak">
              <div className="muted">Streak</div>
              <Heatmap days={14} active={streakDays} />
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}


function NavItem({ label, to = "#", active = false }) {
  const El = to === "#" ? "button" : Link;
  return (
    <El to={to} className={`nav__item ${active ? "nav__item--active" : ""}`}>
      <span className="nav__dot" />
      <span>{label}</span>
    </El>
  );
}

function Progress({ percent = 0 }) {
  const p = Math.max(0, Math.min(100, percent));
  return (
    <div className="bar">
      <div className="bar__fill" style={{ width: `${p}%` }} />
    </div>
  );
}

function Ring({ percent = 0, size = 72, stroke = 8 }) {
  const p = Math.max(0, Math.min(100, percent));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = (p / 100) * c;

  return (
    <svg width={size} height={size} className="ring">
      <circle cx={size/2} cy={size/2} r={r} className="ring__bg" strokeWidth={stroke} fill="none" />
      <circle
        cx={size/2} cy={size/2} r={r}
        className="ring__fg" strokeWidth={stroke} fill="none"
        strokeDasharray={`${dash} ${c - dash}`} strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}
      />
      <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" className="ring__text">
        {p}%
      </text>
    </svg>
  );
}

// Streaks
function Heatmap({ days = 14, active = 5 }) {
  const cells = Array.from({ length: days }, (_, i) => i >= days - active);
  return (
    <div className="heat">
      {cells.map((on, i) => (
        <div key={i} className={`heat__cell ${on ? "heat__cell--on" : ""}`} />
      ))}
    </div>
  );
}