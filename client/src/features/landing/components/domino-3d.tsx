import type { CSSProperties, ReactNode } from "react";

// A 3D domino in CSS: front, sides and top, lit from the upper left. The same tile as in the
// launch film. Opacity goes on each face, never on the tile: Chrome flattens a transparent 3D
// element and its faces collapse.

export type DominoLook = "idle" | "kept" | "pass" | "fail" | "first" | "dim";

const LOOKS: Record<
  DominoLook,
  { face: string; edge: string; ink: string; side: string; top: string }
> = {
  idle: {
    face: "linear-gradient(160deg,#23232a,#15151a)",
    edge: "#3a3a44",
    ink: "#a2a2ae",
    side: "#101014",
    top: "#2c2c34",
  },
  kept: {
    face: "linear-gradient(160deg,#2c2c35,#1a1a20)",
    edge: "#6b6b7a",
    ink: "#f4f4f7",
    side: "#121217",
    top: "#3a3a45",
  },
  pass: {
    face: "linear-gradient(160deg,#2a2a33,#1c1c22)",
    edge: "#d8d8de",
    ink: "#ffffff",
    side: "#121217",
    top: "#3e3e48",
  },
  fail: {
    face: "linear-gradient(160deg,#3a1a1d,#1f0f11)",
    edge: "#f2645a",
    ink: "#ffb1ab",
    side: "#170a0b",
    top: "#4a2226",
  },
  first: {
    face: "linear-gradient(160deg,#a194ff,#7a6af5)",
    edge: "#c7beff",
    ink: "#0b0b10",
    side: "#4b3fb0",
    top: "#b7adff",
  },
  dim: {
    face: "linear-gradient(160deg,#18181c,#111114)",
    edge: "#25252b",
    ink: "#4a4a52",
    side: "#0c0c0f",
    top: "#1c1c21",
  },
};

type DominoProps = {
  n: number;
  size?: number; // width in px; height is 1.9x
  look?: DominoLook;
  fall?: number; // 0 upright, 1 fallen onto the next tile
  lift?: number;
  opacity?: number;
  glow?: number;
  flip?: number; // 0..1, turns over to the fixed face
  delay?: number; // seconds before a change of fall or flip starts, for cascades
};

export function Domino3D({
  n,
  size = 72,
  look = "idle",
  fall = 0,
  lift = 0,
  opacity = 1,
  glow = 0,
  flip = 0,
  delay = 0,
}: DominoProps) {
  const w = size;
  const h = size * 1.9;
  const d = size * 0.32;
  const c = LOOKS[look];
  const back = flip > 0.5;
  const face = (style: CSSProperties): CSSProperties => ({
    position: "absolute",
    opacity,
    ...style,
  });
  return (
    <div
      style={{
        position: "relative",
        width: w,
        height: h,
        transformStyle: "preserve-3d",
        transformOrigin: "100% 100%",
        transform: `translateY(${-lift}px) rotateZ(${68 * fall}deg)`,
        // Gravity on the way down, a small bounce where it lands.
        transition: `transform 0.55s cubic-bezier(.55,.05,.6,1.35) ${delay}s`,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          transformStyle: "preserve-3d",
          transform: `rotateY(${180 * flip}deg)`,
          transition: `transform 0.7s cubic-bezier(.16,1,.3,1) ${delay}s`,
        }}
      >
        <div
          style={face({
            inset: 0,
            borderRadius: w * 0.15,
            background: back ? LOOKS.first.face : c.face,
            border: `2px solid ${back ? LOOKS.first.edge : c.edge}`,
            transform: back ? `rotateY(180deg) translateZ(${d / 2}px)` : `translateZ(${d / 2}px)`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: back ? "center" : "space-between",
            padding: back ? 0 : `${h * 0.09}px 0 ${h * 0.11}px`,
            boxSizing: "border-box",
            color: back ? LOOKS.first.ink : c.ink,
            fontFamily: "var(--font-jetbrains-mono)",
            fontWeight: 600,
            fontSize: w * (back ? 0.3 : 0.36),
            boxShadow: glow
              ? `0 0 ${80 * glow}px rgba(139,124,255,${0.8 * glow})`
              : "0 18px 40px rgba(0,0,0,0.45)",
            transition: "background 0.4s, border-color 0.4s, color 0.4s, box-shadow 0.4s",
          })}
        >
          {back ? (
            "✓"
          ) : (
            <>
              <span>{n}</span>
              <span style={{ width: "62%", height: 2, background: c.ink, opacity: 0.25 }} />
              <span style={{ display: "flex", gap: w * 0.1 }}>
                {[0, 1].map((i) => (
                  <span
                    key={i}
                    style={{
                      width: w * 0.12,
                      height: w * 0.12,
                      borderRadius: "50%",
                      background: c.ink,
                      opacity: 0.6,
                    }}
                  />
                ))}
              </span>
            </>
          )}
        </div>
        <div
          style={face({
            top: 4,
            left: w / 2 - d / 2,
            width: d,
            height: h - 8,
            background: c.side,
            transform: `rotateY(90deg) translateZ(${w / 2 - 1}px)`,
          })}
        />
        <div
          style={face({
            top: 4,
            left: w / 2 - d / 2,
            width: d,
            height: h - 8,
            background: c.side,
            transform: `rotateY(-90deg) translateZ(${w / 2 - 1}px)`,
          })}
        />
        <div
          style={face({
            left: 4,
            top: h / 2 - d / 2,
            width: w - 8,
            height: d,
            background: c.top,
            transform: `rotateX(90deg) translateZ(${h / 2 - 1}px)`,
          })}
        />
      </div>
    </div>
  );
}

/** A row of dominoes seen from slightly above and to the left. */
export function DominoStage({
  children,
  tiltX = -14,
  tiltY = -18,
}: {
  children: ReactNode;
  tiltX?: number;
  tiltY?: number;
}) {
  return (
    <div style={{ perspective: 1600, perspectiveOrigin: "50% 30%" }}>
      <div
        style={{
          transformStyle: "preserve-3d",
          transform: `rotateX(${tiltX}deg) rotateY(${tiltY}deg)`,
        }}
      >
        {children}
      </div>
    </div>
  );
}
