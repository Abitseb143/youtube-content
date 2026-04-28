"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public code: string, message: string, public detail: unknown, public status: number) {
    super(message);
  }
}

type ApiEnvelope<T> = T | { error: { code: string; message: string; detail: unknown } };

async function parseEnvelope<T>(resp: Response): Promise<T> {
  const body = (await resp.json()) as ApiEnvelope<T>;
  if (!resp.ok || (typeof body === "object" && body !== null && "error" in body)) {
    const err = (body as { error: { code: string; message: string; detail: unknown } }).error;
    throw new ApiError(err?.code ?? "unknown", err?.message ?? resp.statusText, err?.detail, resp.status);
  }
  return body as T;
}

export function useApi() {
  const { getToken } = useAuth();

  const request = useCallback(
    async <T>(path: string, init: RequestInit = {}): Promise<T> => {
      const token = await getToken();
      const headers = new Headers(init.headers);
      headers.set("content-type", "application/json");
      if (token) headers.set("authorization", `Bearer ${token}`);
      const resp = await fetch(`${BASE}${path}`, { ...init, headers });
      return parseEnvelope<T>(resp);
    },
    [getToken],
  );

  return { request };
}

export interface MeResponse {
  id: string;
  email: string;
  credit_balance: number;
}
