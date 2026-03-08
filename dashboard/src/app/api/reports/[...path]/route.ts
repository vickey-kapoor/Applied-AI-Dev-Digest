import { NextRequest, NextResponse } from 'next/server';

function getDefaultRepo(): string {
  if (process.env.GITHUB_REPO) {
    return process.env.GITHUB_REPO;
  }

  const owner = process.env.VERCEL_GIT_REPO_OWNER;
  const slug = process.env.VERCEL_GIT_REPO_SLUG;

  if (owner && slug) {
    return `${owner}/${slug}`;
  }

  return 'vickey-kapoor/ai-research-whatsapp-digest';
}

function getBranchesToTry(): string[] {
  const configured = process.env.GITHUB_BRANCH;
  const vercelRef = process.env.VERCEL_GIT_COMMIT_REF;

  return [configured, vercelRef, 'main', 'master'].filter(
    (branch, index, arr): branch is string => Boolean(branch) && arr.indexOf(branch) === index
  );
}

async function fetchReportFromGithub(path: string): Promise<Response | null> {
  const repo = getDefaultRepo();
  const base = `https://raw.githubusercontent.com/${repo}`;

  for (const branch of getBranchesToTry()) {
const DEFAULT_REPO = process.env.GITHUB_REPO ?? 'vickey-kapoor/ai-research-whatsapp-digest';
const DEFAULT_BRANCH = process.env.GITHUB_BRANCH ?? 'main';

async function fetchReportFromGithub(path: string): Promise<Response | null> {
  const base = `https://raw.githubusercontent.com/${DEFAULT_REPO}`;

  const branchesToTry = [DEFAULT_BRANCH, 'master'].filter(
    (branch, index, arr) => arr.indexOf(branch) === index
  );

  for (const branch of branchesToTry) {
    const githubUrl = `${base}/${branch}/reports/${path}`;
    const response = await fetch(githubUrl, {
      next: { revalidate: 3600 },
    });

    if (response.ok) {
      return response;
    }
  }

  return null;
}

export async function GET(
  _request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    const filePath = params.path.join('/').replace(/^reports\//, '');

    if (filePath.includes('..')) {
      return new NextResponse('Invalid path', { status: 400 });
    }

    const response = await fetchReportFromGithub(filePath);

    if (!response) {
      return new NextResponse('File not found', { status: 404 });
    }

    const arrayBuffer = await response.arrayBuffer();
    const contentType = filePath.endsWith('.pdf') ? 'application/pdf' : 'application/octet-stream';

    return new NextResponse(arrayBuffer, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `inline; filename="${filePath.split('/').pop()}"`,
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (error) {
    console.error('Error serving report:', error);
    return new NextResponse('Internal server error', { status: 500 });
  }
}
