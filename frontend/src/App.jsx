import React, { useEffect, useState } from 'react'
import {
  DndContext,
  closestCorners,
  pointerWithin,
  useDroppable,
  PointerSensor,
  useSensor,
  useSensors
} from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import api from './api'

// Prefer the destination column (id "status-<id>") under the pointer.
// The dragged card itself is ignored, otherwise it is detected as the
// drop target and the issue never moves.
function boardCollisionDetection(args) {
  const activeId = String(args.active.id)

  const pointerHits = pointerWithin(args).filter(
    collision => String(collision.id) !== activeId
  )

  const columnHit = pointerHits.find(
    collision => String(collision.id).startsWith('status-')
  )

  if (columnHit) return [columnHit]
  if (pointerHits.length > 0) return pointerHits

  // Pointer is outside every column: fall back to the nearest one.
  return closestCorners(args).filter(
    collision => String(collision.id) !== activeId
  )
}

function SortableIssue({ issue, projectKey, onOpen }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: issue.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    touchAction: 'none'
  }

  return (
    <article
      ref={setNodeRef}
      style={style}
      className="issue"
      {...attributes}
      {...listeners}
      onClick={() => onOpen(issue)}
    >
      <small>{projectKey || 'TASK'}-{issue.id}</small>
      <strong>{issue.title}</strong>
      <span className={'priority ' + issue.priority.toLowerCase()}>
        {issue.priority}
      </span>
    </article>
  )
}

function DroppableColumn({ status, children }) {
  const { setNodeRef, isOver } = useDroppable({
    id: `status-${status.id}`
  })

  return (
    <section
      ref={setNodeRef}
      className="column"
      style={{
        minHeight: '390px',
        background: isOver ? '#e0e8ff' : undefined,
        outline: isOver ? '2px dashed #3457d5' : undefined
      }}
    >
      {children}
    </section>
  )
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('access') || '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const [workspaces, setWorkspaces] = useState([])
  const [workspace, setWorkspace] = useState('')
  const [projects, setProjects] = useState([])
  const [issues, setIssues] = useState([])
  const [statuses, setStatuses] = useState([])

  const [newWorkspace, setNewWorkspace] = useState('')
  const [newProject, setNewProject] = useState('')
  const [newIssue, setNewIssue] = useState('')

  const [selectedIssue, setSelectedIssue] = useState(null)
  const [comment, setComment] = useState('')
  const [notice, setNotice] = useState('')
  const [view, setView] = useState('board')
  const [audit, setAudit] = useState([])
  const [attachments, setAttachments] = useState([])

  // A click still opens the card; the drag starts only after 5px of movement.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  // Only the selected workspace's columns and issues are shown.
  const workspaceId = Number(workspace)
  const workspaceStatuses = statuses.filter(
    status => Number(status.workspace) === workspaceId
  )
  const workspaceIssues = issues.filter(
    issue => Number(issue.workspace) === workspaceId
  )
  const currentWorkspace = workspaces.find(
    item => Number(item.id) === workspaceId
  )
  const isPro = currentWorkspace?.plan === 'PRO'

  async function load() {
    try {
      const [workspaceResponse, statusResponse] = await Promise.all([
        api.get('/workspaces/'),
        api.get('/statuses/')
      ])

      setWorkspaces(workspaceResponse.data)
      setStatuses(statusResponse.data)

      const currentWorkspaceId = workspace || workspaceResponse.data[0]?.id

      if (!currentWorkspaceId) {
        setProjects([])
        setIssues([])
        return
      }

      setWorkspace(String(currentWorkspaceId))

      const [projectResponse, issueResponse] = await Promise.all([
        api.get('/projects/', { params: { workspace: currentWorkspaceId } }),
        api.get('/issues/', { params: { workspace: currentWorkspaceId } })
      ])

      setProjects(projectResponse.data)
      setIssues(issueResponse.data)
    } catch (error) {
      console.error('Load error:', error.response?.data || error)
      setNotice(
        error.response?.data?.detail ||
        'Could not load workspace data. Please check your login.'
      )
    }
  }

  useEffect(() => {
    if (token) {
      load()
    }
  }, [token, workspace])

  async function loadAudit() {
    try {
      const response = await api.get('/audit-events/')
      setAudit(
        response.data
          .filter(event => Number(event.workspace) === workspaceId)
          .slice(0, 50)
      )
    } catch (error) {
      console.error('Audit load error:', error.response?.data || error)
      setNotice('Could not load activity log.')
    }
  }

  useEffect(() => {
    if (token && workspace && view === 'activity') {
      loadAudit()
    }
  }, [token, workspace, view])

  async function login(event) {
    event.preventDefault()

    try {
      const response = await api.post('/token/', {
        username,
        password
      })

      localStorage.setItem('access', response.data.access)
      localStorage.setItem('refresh', response.data.refresh)
      setToken(response.data.access)
      setNotice('Signed in successfully.')
    } catch (error) {
      console.error('Login error:', error.response?.data || error)
      setNotice('Login failed. Please check your username and password.')
    }
  }

  async function register(event) {
    event.preventDefault()

    try {
      await api.post('/auth/register/', {
        username: username.trim(),
        password,
        email: `${username.trim()}@example.com`
      })

      setNotice('Registration successful! Please sign in.')
    } catch (error) {
      console.error('Registration error:', error.response?.data || error)
      setNotice(
        error.response?.data
          ? JSON.stringify(error.response.data)
          : 'Registration failed. Username may already exist or password is too short.'
      )
    }
  }

  async function createWs(event) {
    event.preventDefault()

    if (!newWorkspace.trim()) {
      setNotice('Please enter a workspace name.')
      return
    }

    try {
      const response = await api.post('/workspaces/', {
        name: newWorkspace.trim()
      })

      setNewWorkspace('')
      setWorkspace(String(response.data.id))
      setNotice('Workspace created.')
      await load()
    } catch (error) {
      console.error('Workspace creation error:', error.response?.data || error)
      setNotice(error.response?.data?.detail || 'Workspace creation failed.')
    }
  }

  async function createProject(event) {
    event.preventDefault()

    if (!newProject.trim()) {
      setNotice('Please enter a project name.')
      return
    }

    try {
      const baseKey = newProject
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '')
        .slice(0, 6) || 'TASK'

      await api.post('/projects/', {
        workspace: Number(workspace),
        name: newProject.trim(),
        key: baseKey,
        description: ''
      })

      setNewProject('')
      setNotice('Project created.')
      await load()
    } catch (error) {
      console.error('Project creation error:', error.response?.data || error)
      setNotice(
        error.response?.data?.detail ||
        'Project creation failed. Ensure a workspace is selected.'
      )
    }
  }

  async function createIssue(event) {
    event.preventDefault()

    if (!newIssue.trim()) {
      setNotice('Please enter an issue title.')
      return
    }

    try {
      const project = projects[0]
      const firstStatus = workspaceStatuses[0]

      if (!project || !firstStatus) {
        setNotice('Create a project and workflow statuses first.')
        return
      }

      await api.post('/issues/', {
        workspace: Number(workspace),
        project: project.id,
        title: newIssue.trim(),
        status: firstStatus.id,
        priority: 'MEDIUM'
      })

      setNewIssue('')
      setNotice('Issue created.')
      await load()
    } catch (error) {
      console.error('Issue creation error:', error.response?.data || error)
      setNotice(
        error.response?.data?.detail ||
        'Issue creation failed. Check the selected project and workspace.'
      )
    }
  }

  async function moveIssue(event) {
    const draggedId = String(event.active.id)
    const droppedId = event.over ? String(event.over.id) : ''

    if (!droppedId) {
      return
    }

    const draggedIssue = issues.find(
      issue => String(issue.id) === draggedId
    )

    // A column drop target is "status-<id>".
    // A card drop target is the card's issue id, so use that card's status.
    const destinationStatusId = droppedId.startsWith('status-')
      ? droppedId.slice('status-'.length)
      : issues.find(issue => String(issue.id) === droppedId)?.status

    const destinationStatus = statuses.find(
      status => String(status.id) === String(destinationStatusId)
    )

    if (!draggedIssue || !destinationStatus) {
      console.warn('Drag/drop target could not be resolved:', {
        draggedId,
        droppedId,
        destinationStatusId
      })
      return
    }

    if (String(draggedIssue.status) === String(destinationStatus.id)) {
      return
    }

    // Move the card on screen straight away.
    setIssues(currentIssues =>
      currentIssues.map(issue =>
        String(issue.id) === draggedId
          ? { ...issue, status: destinationStatus.id }
          : issue
      )
    )

    try {
      setNotice('Moving issue...')

      await api.patch(`/issues/${draggedId}/move/`, {
        status: destinationStatus.id
      })

      setNotice(`Issue moved to ${destinationStatus.name}.`)
      await load()
    } catch (error) {
      console.error('Move issue error:', error.response?.data || error)
      setNotice(
        error.response?.data?.detail ||
        JSON.stringify(error.response?.data || 'Could not move issue.')
      )
      // Put the card back where the server says it is.
      await load()
    }
  }

  async function loadAttachments(issueId) {
    try {
      const response = await api.get('/attachments/', {
        params: { issue: issueId }
      })
      setAttachments(response.data)
    } catch (error) {
      console.error('Attachment load error:', error.response?.data || error)
      setAttachments([])
    }
  }

  useEffect(() => {
    if (selectedIssue) {
      loadAttachments(selectedIssue.id)
    } else {
      setAttachments([])
    }
  }, [selectedIssue])

  async function uploadAttachment(event) {
    const input = event.target
    const file = input.files[0]

    if (!file || !selectedIssue) {
      return
    }

    const formData = new FormData()
    formData.append('issue', selectedIssue.id)
    formData.append('file', file)

    try {
      await api.post('/attachments/', formData)
      setNotice('File attached.')
      await loadAttachments(selectedIssue.id)
    } catch (error) {
      console.error('Upload error:', error.response?.data || error)
      setNotice(error.response?.data?.detail || 'File upload failed.')
    }

    input.value = ''
  }

  async function addComment(event) {
    event.preventDefault()

    if (!selectedIssue || !comment.trim()) {
      return
    }

    try {
      await api.post('/comments/', {
        issue: selectedIssue.id,
        body: comment.trim()
      })

      setComment('')
      setNotice('Comment added.')
    } catch (error) {
      console.error('Comment error:', error.response?.data || error)
      setNotice('Comment failed. Check issue membership.')
    }
  }

  async function billing() {
    try {
      const response = await api.post('/billing/checkout/', {
        workspace: Number(workspace)
      })

      window.location.href = response.data.checkout_url
    } catch (error) {
      setNotice(
        error.response?.data?.detail ||
        'Stripe test billing is not configured yet.'
      )
    }
  }

  function logout() {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    setToken('')
    setWorkspace('')
    setWorkspaces([])
    setProjects([])
    setIssues([])
    setStatuses([])
    setSelectedIssue(null)
    setNotice('')
  }

  if (!token) {
    return (
      <main className="auth">
        <section className="auth-card">
          <div className="brand-mark">N</div>
          <h1>NexTask</h1>
          <p>One workspace. Every project in sync.</p>

          <form onSubmit={login}>
            <input
              placeholder="Username"
              value={username}
              onChange={event => setUsername(event.target.value)}
              required
            />

            <input
              type="password"
              placeholder="Password (min. 8 characters)"
              value={password}
              onChange={event => setPassword(event.target.value)}
              required
            />

            <button type="submit">Sign in</button>

            <button
              type="button"
              className="secondary"
              onClick={register}
            >
              Create account
            </button>
          </form>

          <p className="hint">
            Create your account first, then sign in with your credentials.
          </p>

          {notice && <p className="notice">{notice}</p>}
        </section>
      </main>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">N</span>
          <b>NexTask</b>
        </div>

        <p className="muted">WORKSPACE</p>

        <select
          value={workspace}
          onChange={event => setWorkspace(event.target.value)}
        >
          {workspaces.map(item => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>

        {currentWorkspace && (
          <span
            style={{
              width: 'max-content',
              padding: '4px 10px',
              borderRadius: '999px',
              fontSize: '11px',
              fontWeight: 700,
              background: isPro ? '#ecfdf5' : '#eef2ff',
              color: isPro ? '#0f9f6e' : '#3457d5'
            }}
          >
            {isPro ? 'PRO PLAN' : 'FREE PLAN'}
          </span>
        )}

        <form onSubmit={createWs} className="inline-form">
          <input
            placeholder="New workspace"
            value={newWorkspace}
            onChange={event => setNewWorkspace(event.target.value)}
          />
          <button type="submit">+</button>
        </form>

        <nav>
          <a
            className={view === 'board' ? 'active' : ''}
            style={{ cursor: 'pointer' }}
            onClick={() => setView('board')}
          >
            ▦ Board
          </a>
          <a
            className={view === 'activity' ? 'active' : ''}
            style={{ cursor: 'pointer' }}
            onClick={() => setView('activity')}
          >
            ☰ Activity
          </a>
          <a>◷ Sprints</a>
          <a>⚙ Settings</a>
        </nav>

        <div className="sidebar-bottom">
          <button className="secondary" onClick={billing}>
            Upgrade plan
          </button>

          <button className="ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main">
        <header>
          <div>
            <p className="muted">PROJECT MANAGEMENT / WORKSPACE</p>
            <h1>{view === 'board' ? 'Project board' : 'Activity log'}</h1>
          </div>

          <span className="avatar">
            {username.slice(0, 1).toUpperCase() || 'U'}
          </span>
        </header>

        {notice && <div className="notice">{notice}</div>}

        {view === 'board' && (
        <section className="toolbar">
          <form onSubmit={createProject}>
            <input
              placeholder="New project name"
              value={newProject}
              onChange={event => setNewProject(event.target.value)}
            />
            <button type="submit">Create project</button>
          </form>

          <form onSubmit={createIssue}>
            <input
              placeholder="New issue title"
              value={newIssue}
              onChange={event => setNewIssue(event.target.value)}
            />
            <button type="submit">Add issue</button>
          </form>
        </section>
        )}

        {view === 'board' && (
        <DndContext
          sensors={sensors}
          collisionDetection={boardCollisionDetection}
          onDragEnd={moveIssue}
        >
          <div className="board">
            {workspaceStatuses.map(status => {
              const columnIssues = workspaceIssues.filter(
                issue => String(issue.status) === String(status.id)
              )

              return (
                <DroppableColumn key={status.id} status={status}>
                  <div className="column-head">
                    <span
                      className="dot"
                      style={{ background: status.color }}
                    />

                    <b>{status.name}</b>

                    <span className="count">{columnIssues.length}</span>
                  </div>

                  <SortableContext
                    items={columnIssues.map(issue => issue.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    {columnIssues.map(issue => (
                      <SortableIssue
                        key={issue.id}
                        issue={issue}
                        projectKey={
                          projects.find(project => project.id === issue.project)?.key
                        }
                        onOpen={setSelectedIssue}
                      />
                    ))}
                  </SortableContext>
                </DroppableColumn>
              )
            })}
          </div>
        </DndContext>
        )}

        {view === 'activity' && (
          <section className="column" style={{ minHeight: 'auto' }}>
            {audit.length === 0 && <p className="muted">No activity yet.</p>}
            {audit.map(event => (
              <article key={event.id} className="issue" style={{ cursor: 'default' }}>
                <strong>{event.action}</strong>
                <small>
                  {event.entity_type} #{event.entity_id}
                  {event.metadata?.from
                    ? ` · ${event.metadata.from} → ${event.metadata.to}`
                    : ''}
                  {' · '}
                  {new Date(event.created_at).toLocaleString()}
                </small>
              </article>
            ))}
          </section>
        )}

        {selectedIssue && (
          <section className="detail">
            <button
              className="close"
              onClick={() => setSelectedIssue(null)}
            >
              ×
            </button>

            <h2>{selectedIssue.title}</h2>

            <p>
              {selectedIssue.description || 'No description provided.'}
            </p>

            <form onSubmit={addComment}>
              <input
                placeholder="Write a comment"
                value={comment}
                onChange={event => setComment(event.target.value)}
              />

              <button type="submit">Comment</button>
            </form>

            <h3 style={{ marginTop: '18px', fontSize: '14px' }}>Attachments</h3>

            {attachments.length === 0 && (
              <p className="muted">No attachments yet.</p>
            )}

            {attachments.map(item => (
              <a
                key={item.id}
                href={item.file}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'block',
                  fontSize: '13px',
                  color: '#3457d5',
                  margin: '4px 0'
                }}
              >
                {decodeURIComponent(item.file.split('/').pop())}
              </a>
            ))}

            <input
              type="file"
              onChange={uploadAttachment}
              style={{ marginTop: '10px', width: '100%' }}
            />
          </section>
        )}

        <footer>
          Connected workspace data is isolated by membership.
          Billing is available in Stripe test mode after configuration.
        </footer>
      </main>
    </div>
  )
}