// Mã vạch Code39 vẽ bằng SVG. Chọn Code39 vì bảng mã ngắn, đủ cho mã phiếu chữ
// hoa và chữ số, không phải thêm thư viện vào bundle chạy trên Raspberry Pi.
const PATTERNS: Record<string, string> = {
  "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn", "4": "nnnwwnnnw",
  "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw", "8": "wnnwnnwnn", "9": "nnwwnnwnn",
  A: "wnnnnwnnw", B: "nnwnnwnnw", C: "wnwnnwnnn", D: "nnnnwwnnw", E: "wnnnwwnnn",
  F: "nnwnwwnnn", G: "nnnnnwwnw", H: "wnnnnwwnn", I: "nnwnnwwnn", J: "nnnnwwwnn",
  K: "wnnnnnnww", L: "nnwnnnnww", M: "wnwnnnnwn", N: "nnnnwnnww", O: "wnnnwnnwn",
  P: "nnwnwnnwn", Q: "nnnnnnwww", R: "wnnnnnwwn", S: "nnwnnnwwn", T: "nnnnwnwwn",
  U: "wwnnnnnnw", V: "nwwnnnnnw", W: "wwwnnnnnn", X: "nwnnwnnnw", Y: "wwnnwnnnn",
  Z: "nwwnwnnnn", "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn", "*": "nwnnwnwnn",
};

export type Bar = { x: number; width: number };

/** Các vạch đen của chuỗi `text`, đơn vị là module hẹp. Ký tự ngoài bảng bị bỏ. */
export function code39Bars(text: string, narrow = 2, wide = 5): { bars: Bar[]; width: number } {
  const chars = `*${text.toUpperCase()}*`.split("").filter((c) => PATTERNS[c]);
  const bars: Bar[] = [];
  let x = 0;
  for (const c of chars) {
    PATTERNS[c].split("").forEach((size, i) => {
      const w = size === "w" ? wide : narrow;
      if (i % 2 === 0) bars.push({ x, width: w });   // phần tử chẵn là vạch đen
      x += w;
    });
    x += narrow;  // khoảng trắng ngăn cách giữa hai ký tự
  }
  return { bars, width: x };
}

export function Code39({ value, height = 48 }: { value: string; height?: number }) {
  const { bars, width } = code39Bars(value);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label={`Mã vạch ${value}`}>
      {bars.map((b, i) => (
        <rect key={i} x={b.x} y={0} width={b.width} height={height} fill="#000" />
      ))}
    </svg>
  );
}
