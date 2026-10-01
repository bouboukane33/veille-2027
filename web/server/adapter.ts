import type { VercelRequest, VercelResponse } from '@vercel/node';
import { handleApi } from './backend.js';

export function handler(path: string) {
  return async (req: VercelRequest, res: VercelResponse) => {
    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(',') : value);
    }
    const request = new Request('https://ccr.invalid' + path, { method: req.method, headers });
    const response = await handleApi(path, request);
    response.headers.forEach((value, key) => res.setHeader(key, value));
    res.status(response.status).send(await response.text());
  };
}
