import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

// GitHub raw content URL for fetching reports in production
const GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/vickey-kapoor/ai-research-whatsapp-digest/master/reports';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    const filePath = params.path.join('/');

    // Validate path to prevent directory traversal
    if (filePath.includes('..')) {
      return new NextResponse('Invalid path', { status: 400 });
    }

    // Try local paths first
    const reportPaths = [
      path.join(process.cwd(), 'reports'),
      path.join(process.cwd(), '..', 'reports'),
    ];

    for (const reportsDir of reportPaths) {
      try {
        const fullPath = path.join(reportsDir, filePath);

        // Ensure file is within reports directory
        if (!fullPath.startsWith(reportsDir)) {
          continue;
        }

        const file = await fs.readFile(fullPath);

        // Determine content type
        let contentType = 'application/octet-stream';
        if (filePath.endsWith('.pdf')) {
          contentType = 'application/pdf';
        }

        return new NextResponse(file, {
          headers: {
            'Content-Type': contentType,
            'Content-Disposition': `inline; filename="${path.basename(filePath)}"`,
          },
        });
      } catch {
        // Continue to next path
      }
    }

    // Fall back to GitHub raw content (for Vercel deployment)
    try {
      const githubUrl = `${GITHUB_RAW_BASE}/${filePath}`;
      const response = await fetch(githubUrl);

      if (response.ok) {
        const arrayBuffer = await response.arrayBuffer();

        let contentType = 'application/octet-stream';
        if (filePath.endsWith('.pdf')) {
          contentType = 'application/pdf';
        }

        return new NextResponse(arrayBuffer, {
          headers: {
            'Content-Type': contentType,
            'Content-Disposition': `inline; filename="${path.basename(filePath)}"`,
            'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
          },
        });
      }
    } catch {
      // Failed to fetch from GitHub
    }

    return new NextResponse('File not found', { status: 404 });
  } catch (error) {
    console.error('Error serving report:', error);
    return new NextResponse('Internal server error', { status: 500 });
  }
}
