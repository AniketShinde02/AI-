import { app, shell, dialog } from 'electron'
import fs from 'fs'
import path from 'path'
import { pathToFileURL } from 'url'

function ensureGalleryDir(): string {
  const galleryDir = path.resolve(app.getPath('userData'), 'Gallery')
  if (!fs.existsSync(galleryDir)) {
    fs.mkdirSync(galleryDir, { recursive: true })
  }
  return galleryDir
}

export async function getGallery() {
  try {
    const galleryDir = ensureGalleryDir()

    const files = fs
      .readdirSync(galleryDir)
      .filter((file) => /\.(png|jpg|jpeg|webp|gif)$/i.test(file))

    return files
      .map((file) => {
        const filePath = path.join(galleryDir, file)
        const stats = fs.statSync(filePath)
        const fileUrl = pathToFileURL(filePath).href

        return {
          filename: file,
          displayName: file.replace(/_\d+_Generated_by_IRIS\.png$/, '').replace(/_/g, ' '),
          path: filePath,
          url: fileUrl,
          createdAt: stats.birthtime
        }
      })
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
  } catch (error) {
    return []
  }
}

export async function saveImageToGallery({
  title,
  base64Data
}: {
  title: string
  base64Data: string
}) {
  try {
    const galleryDir = ensureGalleryDir()

    const safeTitle = (title || 'visual')
      .replace(/[^a-z0-9]/gi, '_')
      .toLowerCase()
      .substring(0, 50)

    const timestamp = Date.now()
    const fileName = `${safeTitle}_${timestamp}_Generated_by_IRIS.png`
    const filePath = path.join(galleryDir, fileName)

    const data = base64Data.replace(/^data:image\/\w+;base64,/, '')
    const buffer = Buffer.from(data, 'base64')

    fs.writeFileSync(filePath, buffer)

    return { success: true, path: filePath }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
}

export async function deleteImage(filename: string): Promise<boolean> {
  try {
    const galleryDir = ensureGalleryDir()
    const filePath = path.join(galleryDir, filename)

    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath)
      return true
    }
    return false
  } catch (e) {
    return false
  }
}

export async function openImageLocation(filePath: string): Promise<void> {
  shell.showItemInFolder(filePath)
}

export async function saveImageExternal(sourcePath: string) {
  try {
    const { filePath } = await dialog.showSaveDialog({
      title: 'Save Image Copy',
      defaultPath: path.basename(sourcePath),
      filters: [{ name: 'Images', extensions: ['png', 'jpg'] }]
    })

    if (filePath) {
      fs.copyFileSync(sourcePath, filePath)
      return { success: true }
    }
    return { canceled: true }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
}
