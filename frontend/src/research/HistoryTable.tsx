import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";

import type { HistoryRow } from "./api";

const columns: ColumnDef<HistoryRow>[] = [
  {
    header: "Time",
    accessorKey: "time",
    cell: ({ getValue }) => formatDate(String(getValue())),
  },
  {
    header: "Type",
    accessorKey: "type",
  },
  {
    header: "Direction",
    accessorKey: "direction",
    cell: ({ getValue }) => getValue<string | null>() ?? "Unavailable",
  },
  {
    header: "Confidence",
    accessorKey: "confidence",
    cell: ({ getValue }) => {
      const value = getValue<number | null>();
      return value === null ? "Unavailable" : `${Math.round(value * 100)}%`;
    },
  },
  {
    header: "Realized Return",
    accessorKey: "realized_return",
    cell: ({ getValue }) => getValue<string | null>() ?? "Unavailable",
  },
  {
    header: "Review",
    accessorKey: "review_outcome",
    cell: ({ getValue }) => getValue<string | null>() ?? "Unavailable",
  },
  {
    header: "Status",
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
    return <div className="empty-state">No saved records for this symbol.</div>;
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
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
