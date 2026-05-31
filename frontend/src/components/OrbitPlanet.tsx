/** Pure CSS orbit planet widget — Star-Rail-inspired */
export default function OrbitPlanet() {
  return (
    <div className="orbit-planet" aria-hidden>
      <div className="orbit-glow" />
      <div className="orbit-ring ring-main" />
      <div className="orbit-ring ring-secondary" />
      <div className="orbit-ring ring-ghost" />
      <div className="planet-core" />
      <div className="orbit-track track-main">
        <div className="orbit-dot dot-a" />
      </div>
      <div className="orbit-track track-secondary">
        <div className="orbit-dot dot-b" />
      </div>
      <div className="orbit-track track-ghost">
        <div className="orbit-dot dot-c" />
      </div>
      <div className="star-particle p1" />
      <div className="star-particle p2" />
      <div className="star-particle p3" />
    </div>
  );
}
