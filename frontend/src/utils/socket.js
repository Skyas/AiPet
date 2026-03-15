/**
 * Socket.IO 客户端单例
 *
 * 设计原则：全局唯一一个 socket 连接。
 * VisionPanel、ChatPanel、以及未来任何需要实时推送的组件，
 * 都从这里取同一个 socket 实例，不会重复建立连接。
 *
 * 使用方式：
 *   import { useSocket } from '@/utils/socket'
 *   const { socket } = useSocket()
 *   socket.on('proactive_message', handler)
 *   socket.off('proactive_message', handler)  // 组件卸载时务必注销
 */

import { io } from 'socket.io-client'

const BASE_URL = 'http://localhost:8001'

let _socket = null

function createSocket() {
    return io(BASE_URL, {
        transports: ['websocket'],     // 跳过 polling，直接用 WebSocket
        reconnectionAttempts: 10,
        reconnectionDelay: 2000,
        timeout: 5000,
    })
}

/**
 * 获取（或创建）全局 socket 实例。
 * 第一次调用时建立连接，后续调用返回同一个实例。
 */
export function getSocket() {
    if (!_socket) {
        _socket = createSocket()

        _socket.on('connect', () => {
            console.log('[Socket.IO] 已连接:', _socket.id)
        })

        _socket.on('disconnect', (reason) => {
            console.log('[Socket.IO] 断开连接:', reason)
        })

        _socket.on('connect_error', (err) => {
            console.warn('[Socket.IO] 连接错误:', err.message)
        })
    }
    return _socket
}

/**
 * Vue 组合式 API 风格的封装，方便在 <script setup> 里使用。
 */
export function useSocket() {
    return { socket: getSocket() }
}