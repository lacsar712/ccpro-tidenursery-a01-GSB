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
  outflowM3: 10,
  inflowM3: 10,
  startAt: nowLocal(),
  operatorName: '场长',
  note: '',
}

export default function WaterChanges() {
  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<WaterChangeStroke[]>([])
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  // 每条进行中冲程各自的结束时刻输入
  const [endInputs, setEndInputs] = useState<Record<number, string>>({})

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selectedPond = ponds.find((p) => p.id === form.pondId)
  const selectedQuarantine = selectedPond?.status === 'quarantine'
  const selectedDry = selectedPond?.status === 'dry'

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (!(form.outflowM3 > 0) || !(form.inflowM3 > 0)) {
      setError('换出与换入立方数都必须为正数')
      return
    }
    if (selectedQuarantine && !form.note.trim()) {
      setError('隔离塘开换水冲程必须填写备注类说明')
      return
    }
    try {
      await api('/api/water-changes', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          startAt: new Date(form.startAt).toISOString(),
          note: form.note.trim() || null,
        }),
      })
      setForm((f) => ({ ...empty, pondId: f.pondId, startAt: nowLocal() }))
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function finish(id: number) {
    setError('')
    const local = endInputs[id]
    if (!local) {
      setError('请选择结束时刻')
      return
    }
    try {
      await api(`/api/water-changes/${id}/finish`, {
        method: 'POST',
        body: JSON.stringify({ endAt: new Date(local).toISOString() }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '结束冲程失败')
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
          冲程挂塘口，进行中禁止该塘投喂；同塘开始时刻前后半小时仅允许一条；结束时自动按换入水默认盐度
          30ppt 追加一条水质样
        </p>
      </header>
      {error && <div className="error">{error}</div>}

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
                {p.pondCode} · {p.species}
                {p.status === 'dry' ? ' · 干塘(禁开)' : ''}
                {p.status === 'quarantine' ? ' · 隔离(需备注)' : ''}
                {p.waterChanging ? ' · 换水中' : ''}
              </option>
            ))}
          </select>
        </label>
        <label>
          开始时刻
          <input
            type="datetime-local"
            value={form.startAt}
            onChange={(e) => setForm({ ...form, startAt: e.target.value })}
            required
          />
        </label>
        <label>
          换出立方数 m³
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={form.outflowM3}
            onChange={(e) => setForm({ ...form, outflowM3: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          换入立方数 m³
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={form.inflowM3}
            onChange={(e) => setForm({ ...form, inflowM3: Number(e.target.value) })}
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
          {selectedQuarantine ? '备注说明（隔离塘必填）' : '备注说明'}
          <input
            value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })}
            placeholder={
              selectedDry
                ? '干塘禁止开换水冲程'
                : selectedQuarantine
                  ? '隔离塘开冲程必须填写备注类说明'
                  : '可选'
            }
          />
        </label>
        <button type="submit" className="btn primary" disabled={selectedDry}>
          开冲程
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>冲程编号</th>
              <th>塘口</th>
              <th>换出 m³</th>
              <th>换入 m³</th>
              <th>开始时刻</th>
              <th>结束时刻</th>
              <th>操作人</th>
              <th>备注</th>
              <th>状态 / 操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const active = r.endAt === null
              return (
                <tr key={r.id}>
                  <td>#{r.id}</td>
                  <td>{pondLabel(r.pondId)}</td>
                  <td>{r.outflowM3}</td>
                  <td>{r.inflowM3}</td>
                  <td>{new Date(r.startAt).toLocaleString()}</td>
                  <td>{r.endAt ? new Date(r.endAt).toLocaleString() : '—'}</td>
                  <td>{r.operatorName}</td>
                  <td>{r.note || '—'}</td>
                  <td>
                    {active ? (
                      <div className="finish-cell">
                        <span className="badge changing">换水中</span>
                        <input
                          type="datetime-local"
                          value={endInputs[r.id] || ''}
                          onChange={(e) =>
                            setEndInputs((s) => ({ ...s, [r.id]: e.target.value }))
                          }
                        />
                        <button className="btn primary" onClick={() => finish(r.id)}>
                          结束冲程
                        </button>
                      </div>
                    ) : (
                      <span className="badge stocked">
                        已结束{r.closingSampleId ? ` · 水质样#${r.closingSampleId}` : ''}
                      </span>
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
