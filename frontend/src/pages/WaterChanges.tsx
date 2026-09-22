import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Pond, WaterChangeStroke } from '../types'

function nowLocal() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

const empty = {
  pondId: 0,
  outVolumeM3: 10,
  inVolumeM3: 10,
  startedAt: nowLocal(),
  operatorName: '场长',
  notes: '',
}

const DEFAULT_SALINITY_PPT = 30

export default function WaterChanges() {
  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<WaterChangeStroke[]>([])
  const [form, setForm] = useState(empty)
  const [finishAt, setFinishAt] = useState<Record<number, string>>({})
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  async function load() {
    const [ps, ws] = await Promise.all([
      api<Pond[]>('/api/ponds'),
      api<WaterChangeStroke[]>('/api/water-changes'),
    ])
    setPonds(ps)
    setRows(ws)
    if (!form.pondId && ps[0]) {
      setForm((f) => ({ ...f, pondId: ps[0].id }))
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  const selectedPond = ponds.find((p) => p.id === form.pondId) || null

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setInfo('')
    try {
      await api('/api/water-changes', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          notes: form.notes.trim() || null,
          startedAt: new Date(form.startedAt).toISOString(),
        }),
      })
      setForm((f) => ({ ...empty, pondId: f.pondId, startedAt: nowLocal() }))
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function finish(id: number) {
    setError('')
    setInfo('')
    const at = finishAt[id] || nowLocal()
    try {
      await api(`/api/water-changes/${id}/finish`, {
        method: 'POST',
        body: JSON.stringify({ endedAt: new Date(at).toISOString() }),
      })
      setInfo(
        `冲程 #${id} 已结束，并已自动追加一条水质样（盐度取换入水约定默认值 ${DEFAULT_SALINITY_PPT} ppt）`,
      )
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '结束失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} (${p.species})` : `#${id}`
  }

  return (
    <div>
      <header className="page-header">
        <h1>换水冲程</h1>
        <p className="muted">
          冲程挂塘口、进行中与投喂互斥；同塘开始时刻前后半小时仅一条；结束自动写水质样（盐度默认 {DEFAULT_SALINITY_PPT}{' '}
          ppt）。干塘禁开，隔离塘须填备注。
        </p>
      </header>
      {error && <div className="error">{error}</div>}
      {info && <div className="info">{info}</div>}

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label>
          塘口
          <select
            value={form.pondId}
            onChange={(e) => setForm({ ...form, pondId: Number(e.target.value) })}
            required
          >
            {ponds.map((p) => (
              <option key={p.id} value={p.id}>
                {p.pondCode} · {p.species} · {p.status}
              </option>
            ))}
          </select>
        </label>
        <label>
          开始时刻
          <input
            type="datetime-local"
            value={form.startedAt}
            onChange={(e) => setForm({ ...form, startedAt: e.target.value })}
            required
          />
        </label>
        <label>
          换出 m³
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={form.outVolumeM3}
            onChange={(e) => setForm({ ...form, outVolumeM3: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          换入 m³
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={form.inVolumeM3}
            onChange={(e) => setForm({ ...form, inVolumeM3: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          操作人
          <input
            value={form.operatorName}
            onChange={(e) => setForm({ ...form, operatorName: e.target.value })}
            required
          />
        </label>
        <label className="span-2">
          备注{selectedPond?.status === 'quarantine' ? '（隔离塘必填）' : ''}
          <input
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </label>
        <button type="submit" className="btn primary">
          开冲程
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>塘口</th>
              <th>换出 m³</th>
              <th>换入 m³</th>
              <th>开始时刻</th>
              <th>结束时刻</th>
              <th>状态</th>
              <th>操作人</th>
              <th>备注</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const active = !r.endedAt
              return (
                <tr key={r.id}>
                  <td>#{r.id}</td>
                  <td>{pondLabel(r.pondId)}</td>
                  <td>{r.outVolumeM3}</td>
                  <td>{r.inVolumeM3}</td>
                  <td>{new Date(r.startedAt).toLocaleString()}</td>
                  <td>{r.endedAt ? new Date(r.endedAt).toLocaleString() : '—'}</td>
                  <td>
                    {active ? (
                      <span className="badge changing">换水中</span>
                    ) : (
                      <span className="badge stocked">已结束</span>
                    )}
                  </td>
                  <td>{r.operatorName}</td>
                  <td>{r.notes || '—'}</td>
                  <td>
                    {active && (
                      <div className="finish-cell">
                        <input
                          type="datetime-local"
                          value={finishAt[r.id] || ''}
                          onChange={(e) =>
                            setFinishAt((m) => ({ ...m, [r.id]: e.target.value }))
                          }
                          placeholder="结束时刻"
                        />
                        <button className="btn ghost" onClick={() => finish(r.id)}>
                          结束
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
