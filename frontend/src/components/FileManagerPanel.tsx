
import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { recordingsApi, searchApi } from '@/api/client'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import {
    Mic,
    Search,
    MoreVertical,
    Trash2,
    Clock,
    FolderPlus,
    Folder,
    FolderOpen,
    Check,
    Move,
    Edit2,
    ExternalLink,
    Loader2
} from 'lucide-react'
import clsx from 'clsx'
import { DeleteConfirmDialog } from './DeleteConfirmDialog'

interface FileManagerPanelProps {
    sourceType: 'realtime' | 'upload';
    pollingInterval?: number;
}

export function FileManagerPanel({ sourceType, pollingInterval = 0 }: FileManagerPanelProps) {
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [searchParams, setSearchParams] = useSearchParams()

    // State
    const [search, setSearch] = useState(searchParams.get('q') || '')
    const [searchScope, setSearchScope] = useState<'all' | 'title' | 'transcript' | 'summary'>((searchParams.get('scope') as any) || 'all')
    const [selectedIds, setSelectedIds] = useState<string[]>([])
    const [selectedFolderId, setSelectedFolderId] = useState<string | null>(searchParams.get('folder_id') || null)

    // Sync selectedFolderId with URL params when navigating back from detail page
    useEffect(() => {
        const urlFolderId = searchParams.get('folder_id')
        if (urlFolderId !== selectedFolderId) {
            setSelectedFolderId(urlFolderId)
        }
    }, [searchParams])

    // Dialog states
    const [showNewFolderDialog, setShowNewFolderDialog] = useState(false)
    const [showMoveDialog, setShowMoveDialog] = useState(false)
    const [showRenameDialog, setShowRenameDialog] = useState(false)
    const [showDeleteDialog, setShowDeleteDialog] = useState(false)
    const [itemsToDelete, setItemsToDelete] = useState<string[]>([])

    const [recordingToRename, setRecordingToRename] = useState<any>(null)

    // Ref for select all checkbox
    const selectAllRef = useRef<HTMLInputElement>(null)

    // Sync URL params
    const updateParams = (updates: Record<string, string | null>) => {
        const newParams = new URLSearchParams(searchParams)
        Object.entries(updates).forEach(([key, value]) => {
            if (value === null) newParams.delete(key)
            else newParams.set(key, value)
        })
        setSearchParams(newParams)
    }

    // Fetch folders
    const { data: folderData } = useQuery({
        queryKey: ['folders', sourceType],
        queryFn: () => recordingsApi.listFolders({ source_type: sourceType }),
        select: (res) => res.data,
    })
    const folders = folderData?.folders || []

    // Note: uncatagorized_count from backend includes ALL recordings. 
    // Ideally backend should filter by source_type too, but for UI reusing existing API is first step.
    const uncategorizedCount = folderData?.uncategorized_count || 0

    // Fetch recordings
    const { data: recordings, isLoading } = useQuery({
        queryKey: ['recordings', sourceType, search, searchScope, selectedFolderId],
        queryFn: async () => {
            const commonParams = {
                source_type: sourceType,
                folder_id: selectedFolderId || undefined,
                uncategorized: selectedFolderId === null,
            }

            if (search && searchScope !== 'title') {
                // Full text search logic
                const res = await searchApi.search({
                    q: search,
                    search_in: searchScope,
                    limit: 50
                })
                const recordingIds = res.data.results.map((r: any) => r.recording_id)
                if (recordingIds.length === 0) return []

                const listRes = await recordingsApi.list({
                    ...commonParams
                })

                const recordingsMap = new Map(listRes.data.map((r: any) => [r.id, r]))
                return recordingIds
                    .filter((id: string) => recordingsMap.has(id))
                    .map((id: string) => {
                        const recording = recordingsMap.get(id) as Record<string, unknown>
                        const searchResult = res.data.results.find((r: any) => r.recording_id === id)
                        return {
                            ...recording,
                            _matchedField: searchResult?.matched_field,
                            _matchedContent: searchResult?.matched_content
                        }
                    })
            }

            // Standard list
            const res = await recordingsApi.list({
                ...commonParams,
                search: search || undefined,
            })
            return res.data
        },
        refetchInterval: pollingInterval,
    })

    // Mutations
    const deleteMutation = useMutation({
        mutationFn: (ids: string[]) => recordingsApi.batchDelete(ids),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['recordings'] })
            queryClient.invalidateQueries({ queryKey: ['folders'] })
            setSelectedIds([])
            setShowDeleteDialog(false)
            setItemsToDelete([])
        },
    })

    const moveMutation = useMutation({
        mutationFn: ({ ids, folderId }: { ids: string[]; folderId: string | null }) =>
            recordingsApi.batchMove(ids, folderId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['recordings'] })
            queryClient.invalidateQueries({ queryKey: ['folders'] })
            setSelectedIds([])
            setShowMoveDialog(false)
        },
    })

    const createFolderMutation = useMutation({
        mutationFn: (name: string) => recordingsApi.createFolder({ name, source_type: sourceType }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['folders'] })
            setShowNewFolderDialog(false)
        },
    })

    const renameMutation = useMutation({
        mutationFn: ({ id, title }: { id: string; title: string }) =>
            recordingsApi.update(id, { title }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['recordings'] })
            setShowRenameDialog(false)
            setRecordingToRename(null)
        },
    })

    // Helper functions
    const toggleSelect = (id: string) => {
        setSelectedIds((prev) =>
            prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
        )
    }

    const selectAll = () => {
        if (recordings) {
            setSelectedIds(recordings.map((r: any) => r.id))
        }
    }

    const deselectAll = () => {
        setSelectedIds([])
    }

    const handleDelete = (id: string) => {
        setItemsToDelete([id])
        setShowDeleteDialog(true)
    }

    // Checkbox indeterminate state
    const isAllSelected = recordings && recordings.length > 0 && selectedIds.length === recordings.length
    const isSomeSelected = selectedIds.length > 0 && selectedIds.length < (recordings?.length || 0)

    useEffect(() => {
        if (selectAllRef.current) {
            selectAllRef.current.indeterminate = isSomeSelected
        }
    }, [isSomeSelected])

    // Detail navigation path - adapts based on source type logic if necessary, 
    // but typically we use the specific route alias for UI consistency:
    // real-time -> navigate(`/recordings/${id}`)
    // upload -> navigate(`/voice-translate/${id}`)
    // BUT backend isolation ensures we only see correct items.
    // Ideally we should use the route that matches the current module.
    const getDetailPath = (id: string) => {
        if (sourceType === 'upload') return `/voice-translate/${id}`
        return `/recordings/${id}`
    }

    return (
        <div className="h-full flex">
            {/* Folder Sidebar */}
            <div className="w-56 flex-shrink-0 border-r border-brand-200/60 dark:border-brand-800/60 bg-brand-50/5 dark:bg-gray-900/50">
                <div className="p-3 border-b border-brand-100 dark:border-brand-800 flex items-center justify-between bg-brand-50/10 dark:bg-gray-800/50">
                    <span className="text-sm font-medium">文件夹</span>
                    <button
                        onClick={() => setShowNewFolderDialog(true)}
                        className="p-1 hover:bg-brand-50 dark:hover:bg-gray-700 rounded transition-colors border border-transparent hover:border-brand-100/50"
                    >
                        <FolderPlus className="w-4 h-4" />
                    </button>
                </div>
                <div className="p-2 space-y-1">
                    <button
                        onClick={() => {
                            setSelectedFolderId(null)
                            updateParams({ folder_id: null })
                        }}
                        className={clsx(
                            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border border-transparent',
                            selectedFolderId === null
                                ? 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border-brand-200/50'
                                : 'hover:bg-brand-50 dark:hover:bg-gray-800 hover:border-brand-100/50'
                        )}
                    >
                        <FolderOpen className="w-4 h-4" />
                        默认文件夹
                        {/* Note: This count might be global/mixed as flagged in backlog */}
                        <span className="ml-auto text-xs text-gray-500">
                            {uncategorizedCount}
                        </span>
                    </button>

                    {folders?.map((folder: any) => (
                        <button
                            key={folder.id}
                            onClick={() => {
                                setSelectedFolderId(folder.id)
                                updateParams({ folder_id: folder.id })
                            }}
                            className={clsx(
                                'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border border-transparent',
                                selectedFolderId === folder.id
                                    ? 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border-brand-200/50'
                                    : 'hover:bg-brand-50 dark:hover:bg-gray-800 hover:border-brand-100/50'
                            )}
                        >
                            <Folder className="w-4 h-4" />
                            {folder.name}
                            <span className="ml-auto text-xs text-gray-500">
                                {folder.recording_count || 0}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Recording List */}
            <div className="flex-1 flex flex-col p-6 overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold">
                        {sourceType === 'upload' ? '上传记录' : '录音记录'}
                    </h2>
                </div>

                {/* Toolbar */}
                <div className="flex items-center gap-4 mb-4">
                    <div className="relative flex-1 max-w-md flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                placeholder={searchScope === 'all' ? "搜索标题、转录、总结..." :
                                    searchScope === 'title' ? "搜索标题..." :
                                        searchScope === 'transcript' ? "搜索转录内容..." : "搜索AI总结..."}
                                value={search}
                                onChange={(e) => {
                                    setSearch(e.target.value)
                                    updateParams({ q: e.target.value || null })
                                }}
                                className="input pl-10"
                            />
                        </div>
                        <select
                            value={searchScope}
                            onChange={(e) => {
                                const val = e.target.value as any
                                setSearchScope(val)
                                updateParams({ scope: val })
                            }}
                            className="input w-24 text-sm"
                        >
                            <option value="all">全部</option>
                            <option value="title">标题</option>
                            <option value="transcript">转录</option>
                            <option value="summary">总结</option>
                        </select>
                    </div>

                    {recordings && recordings.length > 0 && (
                        <div className="flex items-center gap-4">
                            <label className="flex items-center gap-2 cursor-pointer group shrink-0">
                                <input
                                    ref={selectAllRef}
                                    type="checkbox"
                                    checked={isAllSelected}
                                    onChange={(e) => {
                                        if (e.target.checked) {
                                            selectAll()
                                        } else {
                                            deselectAll()
                                        }
                                    }}
                                    className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                                />
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                                    全选
                                </span>
                            </label>
                            {selectedIds.length > 0 && (
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-500">
                                        已选择 {selectedIds.length} 项
                                    </span>
                                    <button
                                        onClick={() => setShowMoveDialog(true)}
                                        className="btn-secondary flex items-center gap-1"
                                    >
                                        <Move className="w-4 h-4" />
                                        移动
                                    </button>
                                    <button
                                        onClick={() => {
                                            setItemsToDelete(selectedIds)
                                            setShowDeleteDialog(true)
                                        }}
                                        className="btn-danger flex items-center gap-1"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        删除
                                    </button>
                                    <button onClick={deselectAll} className="text-sm text-gray-500 hover:text-gray-700">
                                        取消选择
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Recording List */}
                <div className="flex-1 overflow-y-auto">
                    {isLoading ? (
                        <div className="text-center py-12">
                            <Loader2 className="w-8 h-8 animate-spin mx-auto text-brand-500" />
                        </div>
                    ) : recordings && recordings.length > 0 ? (
                        <div className="card divide-y divide-brand-100/50 dark:divide-brand-900/20">
                            {recordings.map((recording: any) => (
                                <div
                                    key={recording.id}
                                    className={clsx(
                                        'flex items-center gap-4 p-4 hover:bg-brand-50/50 dark:hover:bg-gray-800/50 transition-colors',
                                        selectedIds.includes(recording.id) && 'bg-brand-50 dark:bg-brand-900/20'
                                    )}
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedIds.includes(recording.id)}
                                        onChange={() => toggleSelect(recording.id)}
                                        className="w-4 h-4 rounded border-gray-300"
                                    />

                                    <button
                                        onClick={() => navigate(getDetailPath(recording.id), { state: { fromFolder: selectedFolderId } })}
                                        className="flex-1 flex items-center gap-4 text-left"
                                    >
                                        <div className="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                                            <Mic className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-medium truncate">{recording.title}</h3>
                                            <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                                                <span className="flex items-center gap-1">
                                                    <Clock className="w-3 h-3" />
                                                    {Math.floor(recording.duration_seconds / 60)}:{String(recording.duration_seconds % 60).padStart(2, '0')}
                                                </span>
                                                <span>
                                                    {recording.source_lang.toUpperCase()} → {recording.target_lang.toUpperCase()}
                                                </span>
                                                {recording.has_summary && (
                                                    <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded text-xs">
                                                        AI总结
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </button>

                                    <DropdownMenu.Root>
                                        <DropdownMenu.Trigger asChild>
                                            <button className="p-2 hover:bg-brand-50 dark:hover:bg-gray-700 rounded-lg outline-none border border-transparent hover:border-brand-100/50 transition-colors">
                                                <MoreVertical className="w-4 h-4 text-gray-400" />
                                            </button>
                                        </DropdownMenu.Trigger>

                                        <DropdownMenu.Portal>
                                            <DropdownMenu.Content
                                                className="min-w-[160px] bg-white dark:bg-gray-900 rounded-xl shadow-2xl border border-brand-100 dark:border-brand-800 p-1 z-50 animate-in fade-in zoom-in duration-200"
                                                sideOffset={5}
                                                align="end"
                                            >
                                                <DropdownMenu.Item
                                                    onClick={() => navigate(getDetailPath(recording.id))}
                                                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-brand-50 dark:hover:bg-brand-900/30 hover:text-brand-600 dark:hover:text-brand-400 rounded-lg cursor-pointer outline-none"
                                                >
                                                    <ExternalLink className="w-4 h-4" />
                                                    详情
                                                </DropdownMenu.Item>
                                                <DropdownMenu.Item
                                                    onClick={() => {
                                                        setRecordingToRename(recording)
                                                        setShowRenameDialog(true)
                                                    }}
                                                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-brand-50 dark:hover:bg-brand-900/30 hover:text-brand-600 dark:hover:text-brand-400 rounded-lg cursor-pointer outline-none"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                    重命名
                                                </DropdownMenu.Item>
                                                <DropdownMenu.Item
                                                    onClick={() => {
                                                        if (!selectedIds.includes(recording.id)) {
                                                            toggleSelect(recording.id)
                                                        }
                                                        setShowMoveDialog(true)
                                                    }}
                                                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-brand-50 dark:hover:bg-brand-900/30 hover:text-brand-600 dark:hover:text-brand-400 rounded-lg cursor-pointer outline-none"
                                                >
                                                    <Move className="w-4 h-4" />
                                                    移动到文件夹
                                                </DropdownMenu.Item>
                                                <DropdownMenu.Separator className="h-px bg-brand-100 dark:bg-brand-800 my-1" />
                                                <DropdownMenu.Item
                                                    onClick={() => handleDelete(recording.id)}
                                                    className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg cursor-pointer outline-none"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                    删除
                                                </DropdownMenu.Item>
                                            </DropdownMenu.Content>
                                        </DropdownMenu.Portal>
                                    </DropdownMenu.Root>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="card p-12 text-center">
                            <Mic className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-700" />
                            <h3 className="text-lg font-medium mb-2">
                                {sourceType === 'upload' ? '没有上传记录' : '还没有录音'}
                            </h3>
                            <p className="text-gray-500 mb-6">
                                {sourceType === 'upload' ? '请点击上传文件' : '切换到"实时翻译"标签开始录音'}
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* New Folder Dialog */}
            {showNewFolderDialog && (
                <NewFolderDialog
                    onClose={() => setShowNewFolderDialog(false)}
                    onCreate={(name) => createFolderMutation.mutate(name)}
                    isLoading={createFolderMutation.isPending}
                />
            )}

            {/* Move to Folder Dialog */}
            {showMoveDialog && (
                <MoveFolderDialog
                    folders={folders || []}
                    onClose={() => setShowMoveDialog(false)}
                    onMove={(folderId) => moveMutation.mutate({ ids: selectedIds, folderId })}
                    isLoading={moveMutation.isPending}
                />
            )}

            {/* Rename Recording Dialog */}
            {showRenameDialog && recordingToRename && (
                <RenameDialog
                    recording={recordingToRename}
                    onClose={() => {
                        setShowRenameDialog(false)
                        setRecordingToRename(null)
                    }}
                    onRename={(title: string) => renameMutation.mutate({ id: recordingToRename.id, title })}
                    isLoading={renameMutation.isPending}
                />
            )}

            {/* Delete Confirmation Dialog */}
            <DeleteConfirmDialog
                isOpen={showDeleteDialog}
                onClose={() => {
                    setShowDeleteDialog(false)
                    setItemsToDelete([])
                }}
                onConfirm={() => deleteMutation.mutate(itemsToDelete)}
                title="确认删除"
                description={`确定要删除${itemsToDelete.length > 1 ? `选中的 ${itemsToDelete.length} 条` : '这条'}录音吗？此操作不可恢复。`}
                isLoading={deleteMutation.isPending}
            />
        </div>
    )
}

interface NewFolderDialogProps {
    onClose: () => void;
    onCreate: (name: string) => void;
    isLoading: boolean;
}

function NewFolderDialog({ onClose, onCreate, isLoading }: NewFolderDialogProps) {
    const [name, setName] = useState('')
    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-900 rounded-xl w-full max-w-sm p-6 shadow-xl border border-brand-200 dark:border-brand-800">
                <h3 className="text-lg font-semibold mb-4">新建文件夹</h3>
                <input
                    type="text"
                    placeholder="文件夹名称"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input mb-4"
                    autoFocus
                />
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} className="btn-secondary">取消</button>
                    <button
                        onClick={() => onCreate(name)}
                        disabled={!name.trim() || isLoading}
                        className="btn-primary"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : '创建'}
                    </button>
                </div>
            </div>
        </div>
    )
}

interface MoveFolderDialogProps {
    folders: any[];
    onClose: () => void;
    onMove: (folderId: string | null) => void;
    isLoading: boolean;
}

function MoveFolderDialog({ folders, onClose, onMove, isLoading }: MoveFolderDialogProps) {
    const [selected, setSelected] = useState<string | null>(null)
    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-900 rounded-xl w-full max-w-sm p-6 shadow-xl border border-brand-200 dark:border-brand-800">
                <h3 className="text-lg font-semibold mb-4">移动到文件夹</h3>
                <div className="space-y-1 mb-4 max-h-60 overflow-y-auto">
                    <button
                        onClick={() => setSelected(null)}
                        className={clsx(
                            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors border border-transparent',
                            selected === null ? 'bg-brand-100 dark:bg-brand-900/30 border-brand-200/50' : 'hover:bg-brand-50 dark:hover:bg-gray-800 hover:border-brand-100/50'
                        )}
                    >
                        <Folder className="w-4 h-4" />
                        无文件夹
                        {selected === null && <Check className="w-4 h-4 ml-auto text-brand-600" />}
                    </button>
                    {folders.map((folder: any) => (
                        <button
                            key={folder.id}
                            onClick={() => setSelected(folder.id)}
                            className={clsx(
                                'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors border border-transparent',
                                selected === folder.id ? 'bg-brand-100 dark:bg-brand-900/30 border-brand-200/50' : 'hover:bg-brand-50 dark:hover:bg-gray-800 hover:border-brand-100/50'
                            )}
                        >
                            <Folder className="w-4 h-4" />
                            {folder.name}
                            {selected === folder.id && <Check className="w-4 h-4 ml-auto text-brand-600" />}
                        </button>
                    ))}
                </div>
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} className="btn-secondary">取消</button>
                    <button
                        onClick={() => onMove(selected)}
                        disabled={isLoading}
                        className="btn-primary"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : '移动'}
                    </button>
                </div>
            </div>
        </div>
    )
}

interface RenameDialogProps {
    recording: any;
    onClose: () => void;
    onRename: (title: string) => void;
    isLoading: boolean;
}

function RenameDialog({ recording, onClose, onRename, isLoading }: RenameDialogProps) {
    const [title, setTitle] = useState(recording?.title || '')
    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-900 rounded-xl w-full max-w-sm p-6 shadow-xl text-left border border-brand-200 dark:border-brand-800">
                <h3 className="text-lg font-semibold mb-4">重命名录音</h3>
                <input
                    type="text"
                    placeholder="录音标题"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="input mb-4"
                    autoFocus
                />
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} className="btn-secondary">取消</button>
                    <button
                        onClick={() => onRename(title)}
                        disabled={!title.trim() || isLoading || title === recording.title}
                        className="btn-primary"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : '保存'}
                    </button>
                </div>
            </div>
        </div>
    )
}
