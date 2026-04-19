import { NextRequest } from 'next/server';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ docId: string }> },
) {
  const { docId } = await params;
  const apiUrl = process.env.API_URL ?? 'http://localhost:8001';

  const upstream = await fetch(`${apiUrl}/extract/${docId}/stream`, {
    headers: { Accept: 'text/event-stream' },
  });

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => upstream.statusText);
    return new Response(JSON.stringify({ detail: text }), {
      status: upstream.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  });
}
