// 17 个期限桶（1年内按月拆分 m1~m12，5+ 年保持 y10/y15/y20/y30，1Y 单独保留）
// v2 改造（2026-09-18）：
//   - 去掉 1日 (d1) / 7日 (d7) 桶
//   - 一年内由 m1/m3/m6 (3 桶) 拆为 m1~m12 (12 桶)
//   - 删除未填充的死列 m13~m60
export interface BucketItem {
  key: string;
  name: string;
  width: number;
}

export const BUCKETS: BucketItem[] = [
  // 1年内按月（12 桶）
  { key: 'm1',  name: '1M',   width: 55 },
  { key: 'm2',  name: '2M',   width: 55 },
  { key: 'm3',  name: '3M',   width: 55 },
  { key: 'm4',  name: '4M',   width: 55 },
  { key: 'm5',  name: '5M',   width: 55 },
  { key: 'm6',  name: '6M',   width: 55 },
  { key: 'm7',  name: '7M',   width: 55 },
  { key: 'm8',  name: '8M',   width: 55 },
  { key: 'm9',  name: '9M',   width: 55 },
  { key: 'm10', name: '10M',  width: 55 },
  { key: 'm11', name: '11M',  width: 55 },
  { key: 'm12', name: '12M',  width: 55 },
  // 1年 / 长端固定桶
  { key: 'y1',  name: '1Y',   width: 55 },
  { key: 'y10', name: '10Y',  width: 60 },
  { key: 'y15', name: '15Y',  width: 60 },
  { key: 'y20', name: '20Y',  width: 60 },
  { key: 'y30', name: '30Y',  width: 65 },
];

export const TERM_KEYS: string[] = BUCKETS.map((b) => b.key);
export const TERM_NAMES: Record<string, string> = BUCKETS.reduce(
  (acc, b) => ({ ...acc, [b.key]: b.name }),
  {} as Record<string, string>
);