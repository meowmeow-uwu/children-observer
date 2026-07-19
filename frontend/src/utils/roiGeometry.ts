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

/**
 * Validates whether a polygon is closed and has at least 3 points
 */
export const isValidPolygon = (points: ROIPoint[]): boolean => {
  return points.length >= 3;
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
