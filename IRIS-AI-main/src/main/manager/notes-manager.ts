import { app } from 'electron'
import fs from 'fs'
import path from 'path'

function ensureNotesDir(): string {
  const notesDir = path.resolve(app.getPath('userData'), 'Notes')
  if (!fs.existsSync(notesDir)) {
    fs.mkdirSync(notesDir, { recursive: true })
  }
  return notesDir
}

export async function saveNote({ title, content }: { title: string; content: string }) {
  try {
    const notesDir = ensureNotesDir()
    const safeTitle = title.replace(/[^a-z0-9]/gi, '_').toLowerCase()
    const fileName = `${safeTitle}.md`
    const filePath = path.join(notesDir, fileName)

    const fileContent = `# ${title}\n\n${content}`

    fs.writeFileSync(filePath, fileContent, 'utf-8')
    return { success: true, path: filePath }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
}

export async function getNotes() {
  try {
    const notesDir = ensureNotesDir()
    const files = fs.readdirSync(notesDir).filter((f) => f.endsWith('.md'))

    return files
      .map((file) => {
        const filePath = path.join(notesDir, file)
        const stats = fs.statSync(filePath)
        const content = fs.readFileSync(filePath, 'utf-8')

        return {
          filename: file,
          title: file.replace('.md', '').replace(/_/g, ' '),
          content: content,
          createdAt: stats.birthtime,
          path: filePath
        }
      })
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
  } catch (error) {
    return []
  }
}

export async function deleteNote(filename: string): Promise<boolean> {
  try {
    const notesDir = ensureNotesDir()
    const filePath = path.join(notesDir, filename)
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath)
      return true
    }
    return false
  } catch (e) {
    return false
  }
}
