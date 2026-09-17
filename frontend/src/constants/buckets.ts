// 58 个期限桶（5 年内按月拆分 m13~m60，5 年后保持）
export interface BucketItem {
  key: string;
  name: string;
  width: number;
}

export const BUCKETS: BucketItem[] = [
  { key: 'd1',  name: '1日',  width: 55 },
  { key: 'd7',  name: '7日',  width: 55 },
  { key: 'm1',  name: '1M',   width: 55 },
  { key: 'm3',  name: '3M',   width: 55 },
  { key: 'm6',  name: '6M',   width: 55 },
  // 中端按月 13M~60M（48 个月度桶）
  ...Array.from({ length: 48 }, (_, i) => ({
    key: `m${13 + i}`,
    name: `${13 + i}M`,
    width: 50,
  })),
  // 长端固定桶
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