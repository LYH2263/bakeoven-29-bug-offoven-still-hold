import { useEffect, useState } from "react";
import { api } from "../api/client";
type P = { id: number; name: string; ferment_min: number; bake_min: number; proof_off_oven: boolean };
export default function ProductsPage() {
  const [rows, setRows] = useState<P[]>([]);
  const [err, setErr] = useState("");
  useEffect(() => { api<P[]>("/products").then(setRows); }, []);
  async function toggle(p: P) {
    setErr("");
    try {
      const updated = await api<P>(`/products/${p.id}`, { method: "PATCH", body: JSON.stringify({ proof_off_oven: !p.proof_off_oven }) });
      setRows(rs => rs.map(r => (r.id === updated.id ? updated : r)));
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>产品（配方时长）</h2>
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>名称</th><th>发酵 min</th><th>烘烤 min</th><th>合计</th><th>占炉 min</th><th>醒发不占炉</th></tr></thead>
    <tbody>{rows.map(p => <tr key={p.id}><td>{p.name}</td><td className="mono">{p.ferment_min}</td><td className="mono">{p.bake_min}</td>
      <td className="mono">{p.ferment_min + p.bake_min}</td>
      <td className="mono">{p.proof_off_oven ? p.bake_min : p.ferment_min + p.bake_min}</td>
      <td><input type="checkbox" checked={p.proof_off_oven} onChange={() => toggle(p)} title="离炉醒发：仅烘烤段占炉" /></td></tr>)}</tbody></table>
  </>);
}


