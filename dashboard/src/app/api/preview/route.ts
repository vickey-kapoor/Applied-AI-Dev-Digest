import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

export const maxDuration = 60;

const execAsync = promisify(exec);

export async function GET() {
  const projectRoot = path.resolve(process.cwd(), "..");

  try {
    const { stdout, stderr } = await execAsync("python preview.py", {
      cwd: projectRoot,
      timeout: 55_000,
      env: { ...process.env },
    });

    if (stderr) {
      console.error("[PREVIEW] stderr:", stderr);
    }

    try {
      const result = JSON.parse(stdout);
      if (result.error) {
        return NextResponse.json(result, { status: 502 });
      }
      return NextResponse.json(result);
    } catch {
      return NextResponse.json({ error: "Failed to parse preview output" }, { status: 500 });
    }
  } catch (e: unknown) {
    const err = e as { killed?: boolean; message?: string };
    if (err.killed) {
      return NextResponse.json({ error: "Preview timed out — try again" }, { status: 504 });
    }
    console.error("[PREVIEW] exec failed:", err.message);
    return NextResponse.json({ error: "Preview generation failed" }, { status: 500 });
  }
}
