import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";

import type { HistoryRow } from "./api";

const columns: ColumnDef<HistoryRow>[] = [
  {
    header: "日期",
    accessorKey: "time",
    cell: ({ getValue }) => formatDate(String(getValue())),
  },
  {
    header: "股票",
    id: "stock",
    cell: () => "平安银行",
  },
  {
    header: "AI建议",
    accessorKey: "direction",
    cell: ({ getValue }) => getValue<string | null>() ?? "--",
  },
  {
    header: "收益",
    accessorKey: "realized_return",
    cell: ({ getValue }) => getValue<string | null>() ?? "--",
  },
  {
    header: "状态",
    accessorKey: "status",
  },
];

type Props = {
  rows: HistoryRow[];
};

export function HistoryTable({ rows }: Props) {
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (rows.length === 0) {
    return <div className="empty-state">暂无历史预测</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id}>
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext(),
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
