import type {
  BaseRecord,
  CustomParams,
  DataProvider,
  GetListParams,
} from "@refinedev/core";

import { apiClient, type ApiClient } from "../api/client";

type ListResponse<T> = {
  items: T[];
  total?: number;
  count?: number;
};

export const aiosDataProvider = createAiosDataProvider(apiClient);

export function createAiosDataProvider(client: ApiClient = apiClient): DataProvider {
  return {
    getList: async <TData extends BaseRecord = BaseRecord>(
      params: GetListParams,
    ) => {
      const path = listPath(params);
      const response = await client.get<ListResponse<TData>>(path);
      return {
        data: response.items,
        total: response.total ?? response.count ?? response.items.length,
      };
    },
    getOne: async ({ resource, id }) => ({
      data: await client.get(resourcePath(resource, String(id))),
    }),
    create: async ({ resource, variables }) => ({
      data: await client.post(collectionPath(resource), variables),
    }),
    update: async ({ resource, id, variables }) => ({
      data: await client.patch(resourcePath(resource, String(id)), variables),
    }),
    deleteOne: async ({ resource, id }) => ({
      data: await client.delete(resourcePath(resource, String(id))),
    }),
    getApiUrl: () => "",
    custom: async <
      TData extends BaseRecord = BaseRecord,
      TQuery = unknown,
      TPayload = unknown,
    >(
      params: CustomParams<TQuery, TPayload>,
    ) => {
      const { url, method, payload } = params;
      const lowerMethod = method.toLowerCase();
      const data =
        lowerMethod === "get"
          ? await client.get<TData>(url)
          : lowerMethod === "patch"
            ? await client.patch<TData>(url, payload)
            : lowerMethod === "delete"
              ? await client.delete<TData>(url)
              : await client.post<TData>(url, payload);
      return { data };
    },
  };
}

function listPath(params: GetListParams) {
  const url = new URL(collectionPath(params.resource), "http://aios.local");
  const pageSize = params.pagination?.pageSize ?? 50;
  const current =
    params.pagination && "current" in params.pagination
      ? Number(params.pagination.current)
      : params.pagination?.currentPage ?? 1;
  if (params.resource === "simulated-executions" || params.resource === "settlements") {
    url.searchParams.set("page", String(current));
    url.searchParams.set("page_size", String(pageSize));
  } else {
    url.searchParams.set("limit", String(pageSize));
    url.searchParams.set("offset", String((current - 1) * pageSize));
  }
  for (const filter of params.filters ?? []) {
    if ("field" in filter && filter.value !== undefined && filter.value !== null) {
      url.searchParams.set(filter.field, String(filter.value));
    }
  }
  return `${url.pathname}${url.search}`;
}

function collectionPath(resource: string) {
  if (resource === "watchlist") return "/research/watchlist";
  if (resource === "research-runs") return "/research/runs";
  if (resource === "simulated-executions") return "/simulated-executions";
  if (resource === "settlements") return "/settlements";
  if (resource === "learnings") return "/learnings";
  throw new Error(`Unsupported Refine resource: ${resource}`);
}

function resourcePath(resource: string, id: string) {
  return `${collectionPath(resource)}/${encodeURIComponent(id)}`;
}
