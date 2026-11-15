import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

async function proxy(request: NextRequest, path: string[]) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const query = request.nextUrl.searchParams.toString();
  const endpoint = `/api/v1/shop/${path.join("/")}${query ? `?${query}` : ""}`;
  const body =
    request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();

  try {
    const data = await backendFetch(endpoint, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        "X-Request-ID": request.headers.get("x-request-id") || crypto.randomUUID(),
      },
      body,
    });
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.data || error.message || "Shop request failed" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
