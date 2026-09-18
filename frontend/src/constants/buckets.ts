// 64 个期限桶（5 年内按月 m1~m60，长端 y10/y15/y20/y30）
// v3 改造（2026-09-18）：
//   - 5 年内全部按月拆分（m1~m60）
//   - 删除 y1（m12 已代表 12 月 = 1Y）
//   - 长端固定桶 y10/y15/y20/y30 保留
export interface BucketItem {
  key: string;
  name: string;
  width: number;
}

// 1-12 月（年1，12桶）
const year1 = Array.from({ length: 12 }, (_, i) => i + 1).map((n) => ({
  key: `m${n}`,
  name: `${n}M`,
  width: 50,
}));

// 13-24 月（年2，12桶）
const year2 = Array.from({ length: 12 }, (_, i) => i + 13).map((n) => ({
  key: `m${n}`,
  name: `${n}M`,
  width: 50,
}));

// 25-36 月（年3，12桶）
const year3 = Array.from({ length: 12 }, (_, i) => i + 25).map((n) => ({
  key: `m${n}`,
  name: `${n}M`,
  width: 50,
}));

// 37-48 月（年4，12桶）
const year4 = Array.from({ length: 12 }, (_, i) => i + 37).map((n) => ({
  key: `m${n}`,
  name: `${n}M`,
  width: 50,
}));

// 49-60 月（年5，12桶）
const year5 = Array.from({ length: 12 }, (_, i) => i + 49).map((n) => ({
  key: `m${n}`,
  name: `${n}M`,
  width: 50,
}));

// 长端固定桶（4桶）
const longTerm = [
  { key: 'y10', name: '10Y', width: 60 },
  { key: 'y15', name: '15Y', width: 60 },
  { key: 'y20', name: '20Y', width: 60 },
  { key: 'y30', name: '30Y', width: 65 },
];

export const BUCKETS: BucketItem[] = [
  ...year1,
  ...year2,
  ...year3,
  ...year4,
  ...year5,
  ...longTerm,
];

export const TERM_KEYS: string[] = BUCKETS.map((b) => b.key);
export const TERM_NAMES: Record<string, string> = BUCKETS.reduce(
  (acc, b) => ({ ...acc, [b.key]: b.name }),
  {} as Record<string, string>
);

// 分组：1年/2年/3年/4年/5年/长端
export const TERM_GROUPS = [
  { label: '1年 (1-12月)', keys: Array.from({ length: 12 }, (_, i) => `m${i + 1}`) },
  { label: '2年 (13-24月)', keys: Array.from({ length: 12 }, (_, i) => `m${i + 13}`) },
  { label: '3年 (25-36月)', keys: Array.from({ length: 12 }, (_, i) => `m${i + 25}`) },
  { label: '4年 (37-48月)', keys: Array.from({ length: 12 }, (_, i) => `m${i + 37}`) },
  { label: '5年 (49-60月)', keys: Array.from({ length: 12 }, (_, i) => `m${i + 49}`) },
  { label: '长端 (10Y+)', keys: ['y10', 'y15', 'y20', 'y30'] },
];