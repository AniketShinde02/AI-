import { app } from 'electron'
import fs from 'fs/promises'
import path from 'path'

export async function writeFile({
  fileName,
  content
}: {
  fileName: string
  content: string
}): Promise<string> {
  try {
    const isAbsolutePath = fileName.includes('/') || fileName.includes('\\')

    const targetPath = isAbsolutePath ? fileName : path.join(app.getPath('desktop'), fileName)

    await fs.writeFile(targetPath, content, 'utf-8')
    return `Success. File saved to: ${targetPath}`
  } catch (err) {
    return `Error writing file: ${err}`
  }
}
