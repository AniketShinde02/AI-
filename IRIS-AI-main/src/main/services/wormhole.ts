import { startTunnel } from 'untun'

let activeTunnel: any = null

export async function openWormhole(port: number) {
  try {
    if (activeTunnel) {
      await activeTunnel.close()
      activeTunnel = null
    }

    activeTunnel = await startTunnel({
      port,
      acceptCloudflareNotice: true
    })

    const tunnelUrl = await activeTunnel.getURL()

    return {
      success: true,
      url: tunnelUrl,
      password: null
    }
  } catch (err) {
    return { success: false, error: String(err) }
  }
}

export async function closeWormhole() {
  try {
    if (activeTunnel) {
      await activeTunnel.close()
      activeTunnel = null
    }
    return { success: true }
  } catch (err) {
    return { success: false, error: String(err) }
  }
}
