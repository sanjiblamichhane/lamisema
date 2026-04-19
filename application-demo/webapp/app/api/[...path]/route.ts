import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.API_URL ?? 'http://localhost:8001';

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const url = `${API_URL}/${path.join('/')}`;

  const headers = new Headers(req.headers);
  headers.delete('host');

  const init: RequestInit & { duplex?: string } = { method: req.method, headers };

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    init.body = req.body;
    init.duplex = 'half'; // required for streaming request bodies in Node 18+
  }

  let res: Response;
  try {
    res = await fetch(url, init as RequestInit);
  } catch (err) {
    console.error(`[proxy] Failed to reach ${url}:`, err);
    return NextResponse.json({ detail: `API unreachable at ${url}` }, { status: 502 });
  }

  const resHeaders = new Headers(res.headers);
  resHeaders.delete('transfer-encoding');

  return new NextResponse(res.body, { status: res.status, headers: resHeaders });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, { params }: Ctx) {
  return proxy(req, (await params).path);
}
export async function POST(req: NextRequest, { params }: Ctx) {
  return proxy(req, (await params).path);
}
export async function PUT(req: NextRequest, { params }: Ctx) {
  return proxy(req, (await params).path);
}
export async function DELETE(req: NextRequest, { params }: Ctx) {
  return proxy(req, (await params).path);
}
