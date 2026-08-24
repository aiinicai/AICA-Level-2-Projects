/** Simple deterministic radial layout: center node in the middle, contributors arranged in a circle. */
export function radialLayout(nodeCount, { radius = 260, centerX = 400, centerY = 260 } = {}) {
  const positions = [];
  const angleStep = (2 * Math.PI) / Math.max(nodeCount, 1);
  for (let i = 0; i < nodeCount; i++) {
    const angle = i * angleStep - Math.PI / 2;
    positions.push({
      x: centerX + radius * Math.cos(angle) - 90,
      y: centerY + radius * Math.sin(angle) - 30,
    });
  }
  return positions;
}
