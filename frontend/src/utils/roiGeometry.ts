import type { ROIPoint } from "../types";

/**
 * Normalizes absolute coordinates into a [0.0, 1.0] ratio based on bounding box
 */
export const normalizePoint = (
  x: number,
  y: number,
  width: number,
  height: number
): ROIPoint => {
  return {
    x: Math.max(0, Math.min(1, x / width)),
    y: Math.max(0, Math.min(1, y / height))
  };
};

/**
 * Converts normalized [0.0, 1.0] ratios back to absolute canvas pixels
 */
export const denormalizePoint = (
  point: ROIPoint,
  width: number,
  height: number
): { x: number; y: number } => {
  return {
    x: point.x * width,
    y: point.y * height
  };
};

/**
 * Creates 4 boundary vertices of a rectangle from 2 opposite corner points
 */
export const createRectangleFromTwoPoints = (
  p1: ROIPoint,
  p2: ROIPoint
): ROIPoint[] => {
  // Returns points in clockwise order: top-left, top-right, bottom-right, bottom-left
  const xMin = Math.min(p1.x, p2.x);
  const xMax = Math.max(p1.x, p2.x);
  const yMin = Math.min(p1.y, p2.y);
  const yMax = Math.max(p1.y, p2.y);

  return [
    { x: xMin, y: yMin }, // Top-Left
    { x: xMax, y: yMin }, // Top-Right
    { x: xMax, y: yMax }, // Bottom-Right
    { x: xMin, y: yMax }  // Bottom-Left
  ];
};

/** Ngưỡng coi hai điểm là "trùng" (trong không gian chuẩn hóa 0-1) */
const EPSILON = 0.002;

/** Diện tích tối thiểu hợp lệ của vùng (tỷ lệ với diện tích khung hình) */
const MIN_AREA = 0.0025;

/**
 * Validates whether a polygon is closed and has at least 3 points
 * (legacy shallow check — dùng cho các chỗ hiển thị nhanh)
 */
export const isValidPolygon = (points: ROIPoint[]): boolean => {
  return points.length >= 3;
};

export const hasDuplicatePoints = (points: ROIPoint[]): boolean => {
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      const a = points[i];
      const b = points[j];
      if (Math.abs(a.x - b.x) <= EPSILON && Math.abs(a.y - b.y) <= EPSILON) {
        return true;
      }
    }
  }
  return false;
};

const cross = (o: ROIPoint, a: ROIPoint, b: ROIPoint): number => {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
};

const onSegment = (p: ROIPoint, q: ROIPoint, r: ROIPoint): boolean => {
  return (
    q.x <= Math.max(p.x, r.x) && q.x >= Math.min(p.x, r.x) &&
    q.y <= Math.max(p.y, r.y) && q.y >= Math.min(p.y, r.y)
  );
};

export const segmentsIntersect = (p1: ROIPoint, q1: ROIPoint, p2: ROIPoint, q2: ROIPoint): boolean => {
  const o1 = cross(p1, q1, p2);
  const o2 = cross(p1, q1, q2);
  const o3 = cross(p2, q2, p1);
  const o4 = cross(p2, q2, q1);

  if (((o1 > 0 && o2 < 0) || (o1 < 0 && o2 > 0)) && ((o3 > 0 && o4 < 0) || (o3 < 0 && o4 > 0))) {
    return true;
  }
  if (o1 === 0 && onSegment(p1, p2, q1)) return true;
  if (o2 === 0 && onSegment(p1, q2, q1)) return true;
  if (o3 === 0 && onSegment(p2, p1, q2)) return true;
  if (o4 === 0 && onSegment(p2, q1, q2)) return true;
  return false;
};

/** Đa giác tự cắt (bowtie) — các cạnh không kề nhau giao nhau */
export const isSelfIntersecting = (points: ROIPoint[]): boolean => {
  if (points.length < 4) return false;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const p1 = points[i];
    const q1 = points[(i + 1) % n];
    for (let j = i + 1; j < n; j++) {
      if (Math.abs(i - j) <= 1 || (i === 0 && j === n - 1)) continue; // cạnh kề nhau
      const p2 = points[j];
      const q2 = points[(j + 1) % n];
      if (segmentsIntersect(p1, q1, p2, q2)) return true;
    }
  }
  return false;
};

/** Diện tích đa giác (shoelace) trong không gian chuẩn hóa 0-1 */
export const polygonArea = (points: ROIPoint[]): number => {
  if (points.length < 3) return 0;
  let area = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const a = points[i];
    const b = points[(i + 1) % n];
    area += a.x * b.y - b.x * a.y;
  }
  return Math.abs(area) / 2;
};

export interface PolygonValidation {
  valid: boolean;
  error: string | null;
}

/**
 * Validation chặt cho vùng vẽ:
 * - Đủ số điểm (polygon ≥ 3, rectangle = 4).
 * - Không có điểm trùng nhau.
 * - Không tự cắt.
 * - Diện tích ≥ MIN_AREA (0.25% khung hình) — tránh vùng vô nghĩa.
 */
export const validatePolygonStrict = (points: ROIPoint[], type: "polygon" | "rectangle"): PolygonValidation => {
  if (points.length === 0) {
    return { valid: false, error: "Chưa có điểm nào được vẽ." };
  }
  if (type === "polygon" && points.length < 3) {
    return { valid: false, error: "Vùng đa giác cần ít nhất 3 điểm." };
  }
  if (type === "rectangle" && points.length < 4) {
    return { valid: false, error: "Vùng hình chữ nhật chưa hoàn thành vẽ (cần 4 góc)." };
  }
  if (hasDuplicatePoints(points)) {
    return { valid: false, error: "Có các điểm trùng nhau — hãy kéo các góc cách xa nhau hơn." };
  }
  if (type === "polygon" && isSelfIntersecting(points)) {
    return { valid: false, error: "Đa giác tự cắt chính nó — hãy vẽ lại các đỉnh theo thứ tự." };
  }
  const area = polygonArea(points);
  if (area < MIN_AREA) {
    return { valid: false, error: "Vùng quá nhỏ — hãy vẽ rộng hơn ít nhất 0.25% khung hình." };
  }
  return { valid: true, error: null };
};

/**
 * Clamps coordinates between 0 and 1
 */
export const clampPoint = (point: ROIPoint): ROIPoint => {
  return {
    x: Math.max(0, Math.min(1, point.x)),
    y: Math.max(0, Math.min(1, point.y))
  };
};
