import { describe, it, expect } from "vitest";
import {
  createRectangleFromTwoPoints,
  hasDuplicatePoints,
  isSelfIntersecting,
  polygonArea,
  segmentsIntersect,
  validatePolygonStrict,
  clampPoint,
} from "./roiGeometry";
import type { ROIPoint } from "../types";

const rect: ROIPoint[] = [
  { x: 0.1, y: 0.1 },
  { x: 0.5, y: 0.1 },
  { x: 0.5, y: 0.6 },
  { x: 0.1, y: 0.6 },
];

describe("createRectangleFromTwoPoints", () => {
  it("tạo 4 góc theo chiều kim đồng hồ từ 2 góc đối diện", () => {
    const pts = createRectangleFromTwoPoints({ x: 0.2, y: 0.4 }, { x: 0.8, y: 0.7 });
    expect(pts).toEqual([
      { x: 0.2, y: 0.4 },
      { x: 0.8, y: 0.4 },
      { x: 0.8, y: 0.7 },
      { x: 0.2, y: 0.7 },
    ]);
  });
});

describe("hasDuplicatePoints", () => {
  it("phát hiện điểm trùng", () => {
    expect(hasDuplicatePoints([...rect, { x: 0.5005, y: 0.1 }])).toBe(true);
  });

  it("chấp nhận các điểm phân biệt", () => {
    expect(hasDuplicatePoints(rect)).toBe(false);
  });
});

describe("segmentsIntersect / isSelfIntersecting", () => {
  it("hai đoạn chéo nhau thì cắt", () => {
    expect(segmentsIntersect(
      { x: 0, y: 0 }, { x: 1, y: 1 },
      { x: 0, y: 1 }, { x: 1, y: 0 },
    )).toBe(true);
  });

  it("hai đoạn song song không cắt", () => {
    expect(segmentsIntersect(
      { x: 0, y: 0 }, { x: 1, y: 0 },
      { x: 0, y: 1 }, { x: 1, y: 1 },
    )).toBe(false);
  });

  it("đa giác bowtie (tự cắt) bị phát hiện", () => {
    const bowtie: ROIPoint[] = [
      { x: 0.1, y: 0.1 },
      { x: 0.9, y: 0.9 },
      { x: 0.9, y: 0.1 },
      { x: 0.1, y: 0.9 },
    ];
    expect(isSelfIntersecting(bowtie)).toBe(true);
  });

  it("hình chữ nhật bình thường không tự cắt", () => {
    expect(isSelfIntersecting(rect)).toBe(false);
  });
});

describe("polygonArea", () => {
  it("tính diện tích chuẩn hóa", () => {
    expect(polygonArea(rect)).toBeCloseTo(0.2, 5); // 0.4 x 0.5
  });
});

describe("validatePolygonStrict", () => {
  it("polygon hợp lệ với đủ điểm + diện tích", () => {
    const r = validatePolygonStrict(rect, "rectangle");
    expect(r.valid).toBe(true);
    expect(r.error).toBeNull();
  });

  it("polygon thiếu điểm → lỗi", () => {
    expect(validatePolygonStrict([rect[0], rect[1]], "polygon").valid).toBe(false);
  });

  it("vùng quá nhỏ → lỗi", () => {
    const tiny = [
      { x: 0.5, y: 0.5 },
      { x: 0.51, y: 0.5 },
      { x: 0.51, y: 0.51 },
    ];
    expect(validatePolygonStrict(tiny, "polygon").valid).toBe(false);
  });

  it("đa giác tự cắt → lỗi", () => {
    const bowtie: ROIPoint[] = [
      { x: 0.1, y: 0.1 },
      { x: 0.9, y: 0.9 },
      { x: 0.9, y: 0.1 },
      { x: 0.1, y: 0.9 },
    ];
    expect(validatePolygonStrict(bowtie, "polygon").valid).toBe(false);
  });

  it("điểm trùng → lỗi", () => {
    const dup = [...rect, { x: 0.101, y: 0.101 }];
    expect(validatePolygonStrict(dup, "polygon").valid).toBe(false);
  });
});

describe("clampPoint", () => {
  it("giới hạn về [0,1]", () => {
    expect(clampPoint({ x: -0.5, y: 1.5 })).toEqual({ x: 0, y: 1 });
  });
});
