import { NavLink } from "react-router-dom";

export default function ProjectNav({ id }: { id: string }) {
  const base = `/p/${id}`;
  return (
    <div className="tabs">
      <NavLink to={`${base}/media`}>Media</NavLink>
      <NavLink to={`${base}/run`}>Run</NavLink>
      <NavLink to={`${base}/review`}>Review</NavLink>
      <NavLink to={`${base}/export`}>Export</NavLink>
    </div>
  );
}
