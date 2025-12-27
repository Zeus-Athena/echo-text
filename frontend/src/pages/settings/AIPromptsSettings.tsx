import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { promptsApi } from '@/api/client'
import { PromptTemplate, PromptTemplateCreate, PromptTemplateUpdate } from '@/api/types'
import { useToast } from '@/components/Toast'
import { Plus, Edit2, Trash2, Check, X, FileText, Sparkles, MessageSquare, Loader2 } from 'lucide-react'

// Template Types
const TEMPLATE_TYPES = [
    { id: 'translation', name: '翻译', icon: Sparkles },
    { id: 'summary', name: '摘要', icon: FileText },
    { id: 'dictionary', name: '词典', icon: MessageSquare },
]

export default function AIPromptsSettings() {
    const [selectedType, setSelectedType] = useState('translation')
    const [isEditing, setIsEditing] = useState(false)
    const [currentTemplate, setCurrentTemplate] = useState<PromptTemplate | null>(null)
    const [formData, setFormData] = useState<PromptTemplateCreate>({
        name: '',
        template_type: 'translation',
        content: '',
        is_active: false,
    })

    const queryClient = useQueryClient()
    const { success, error } = useToast()

    // Fetch templates
    const { data: templates = [], isLoading } = useQuery({
        queryKey: ['prompts', selectedType],
        queryFn: () => promptsApi.list(selectedType),
        select: (res) => res.data,
    })

    // Mutations
    const createMutation = useMutation({
        mutationFn: (data: PromptTemplateCreate) => promptsApi.create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['prompts'] })
            success('提示词创建成功')
            closeModal()
        },
        onError: () => error('创建失败'),
    })

    const updateMutation = useMutation({
        mutationFn: (variables: PromptTemplateCreate) => promptsApi.update(currentTemplate!.id, variables as PromptTemplateUpdate),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['prompts'] })
            success('提示词更新成功')
            closeModal()
        },
        onError: () => error('更新失败'),
    })

    const deleteMutation = useMutation({
        mutationFn: (id: string) => promptsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['prompts'] })
            success('提示词已删除')
        },
        onError: () => error('删除失败'),
    })

    // Handlers
    const openCreateModal = () => {
        setFormData({
            name: '',
            template_type: selectedType,
            content: getDefaultContent(selectedType),
            is_active: false,
        })
        setCurrentTemplate(null)
        setIsEditing(true)
    }

    const openEditModal = (template: PromptTemplate) => {
        setFormData({
            name: template.name,
            template_type: template.template_type,
            content: template.content,
            is_active: template.is_active,
        })
        setCurrentTemplate(template)
        setIsEditing(true)
    }

    const closeModal = () => {
        setIsEditing(false)
        setCurrentTemplate(null)
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (currentTemplate) {
            updateMutation.mutate(formData)
        } else {
            createMutation.mutate(formData)
        }
    }

    const getDefaultContent = (type: string) => {
        switch (type) {
            case 'translation': return 'Translate the following text to {{target_lang}}:\n\n{{text}}'
            case 'summary': return 'Summarize the following text:\n\n{{text}}'
            default: return ''
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-brand-700 dark:text-brand-300">
                    自定义提示词模板
                </h2>
                <button
                    onClick={openCreateModal}
                    className="btn-primary flex items-center gap-2 text-sm"
                >
                    <Plus className="w-4 h-4" />
                    新建模板
                </button>
            </div>

            {/* Type Tabs */}
            <div className="flex gap-2 border-b border-brand-100 dark:border-brand-800 pb-px">
                {TEMPLATE_TYPES.map(type => (
                    <button
                        key={type.id}
                        onClick={() => setSelectedType(type.id)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${selectedType === type.id
                            ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                            }`}
                    >
                        <type.icon className="w-4 h-4" />
                        {type.name}
                    </button>
                ))}
            </div>

            {/* Templates Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {isLoading ? (
                    <div className="col-span-full py-8 text-center text-gray-500">
                        加载中...
                    </div>
                ) : templates.length === 0 ? (
                    <div className="col-span-full py-12 text-center bg-gray-50 dark:bg-gray-800/50 rounded-lg dashed-border">
                        <p className="text-gray-500 mb-4">暂无 {TEMPLATE_TYPES.find(t => t.id === selectedType)?.name} 模板</p>
                        <button
                            onClick={openCreateModal}
                            className="text-blue-600 hover:underline text-sm"
                        >
                            创建第一个模板
                        </button>
                    </div>
                ) : (
                    templates.map((template: PromptTemplate) => (
                        <div
                            key={template.id}
                            className={`group relative p-4 rounded-xl border transition-all ${template.is_active
                                ? 'border-brand-200 bg-brand-50/30 dark:border-brand-800 dark:bg-brand-900/10 shadow-sm outline outline-1 outline-brand-500/20'
                                : 'border-brand-100 bg-white dark:border-brand-800 dark:bg-gray-800/50 hover:border-brand-200 dark:hover:border-brand-700'
                                }`}
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <h3 className="font-semibold text-brand-700 dark:text-brand-300">
                                            {template.name}
                                        </h3>
                                        {template.is_active && (
                                            <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-brand-500 text-white rounded">
                                                Active
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-xs text-gray-500 mt-1">
                                        更新于 {new Date(template.updated_at).toLocaleDateString()}
                                    </p>
                                </div>
                                <div className="flex items-center gap-1 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => openEditModal(template)}
                                        className="p-1.5 text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                                    >
                                        <Edit2 className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (confirm('确定要删除这个模板吗？')) {
                                                deleteMutation.mutate(template.id)
                                            }
                                        }}
                                        className="p-1.5 text-gray-500 hover:text-red-600 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                            <div className="relative">
                                <pre className="text-sm font-mono text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-900/50 p-3 rounded-lg overflow-hidden h-24 text-ellipsis">
                                    {template.content}
                                </pre>
                                <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-gray-50 dark:from-gray-900/50 to-transparent pointer-events-none" />
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Modal */}
            {isEditing && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-brand-200 dark:border-brand-800">
                        <div className="px-6 py-4 border-b border-brand-100 dark:border-brand-700 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800">
                            <h3 className="text-lg font-semibold text-brand-700 dark:text-white">
                                {currentTemplate ? '编辑模板' : '新建模板'}
                            </h3>
                            <button
                                onClick={closeModal}
                                className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    模板名称
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-brand-200 dark:border-brand-800 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition-shadow"
                                    placeholder="例如：学术翻译"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    提示词内容
                                </label>
                                <div className="relative">
                                    <textarea
                                        required
                                        rows={8}
                                        value={formData.content}
                                        onChange={e => setFormData({ ...formData, content: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-brand-200 dark:border-brand-800 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition-shadow resize-none"
                                        placeholder="Translate {{text}} to..."
                                    />
                                    <div className="absolute right-2 bottom-2 text-[10px] text-gray-400 pointer-events-none bg-white/50 dark:bg-gray-800/50 px-1 rounded">
                                        可用变量: {'{{text}}'}, {'{{source_lang}}'}, {'{{target_lang}}'}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${formData.is_active ? 'bg-brand-600' : 'bg-gray-200 dark:bg-gray-600'
                                        }`}
                                >
                                    <span
                                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${formData.is_active ? 'translate-x-6' : 'translate-x-1'
                                            }`}
                                    />
                                </button>
                                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                                    设为默认模板
                                </span>
                            </div>

                            <div className="pt-4 flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={closeModal}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors border border-gray-200 dark:border-gray-700"
                                >
                                    取消
                                </button>
                                <button
                                    type="submit"
                                    disabled={createMutation.isPending || updateMutation.isPending}
                                    className="btn-primary flex items-center gap-2"
                                >
                                    {(createMutation.isPending || updateMutation.isPending) && (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    )}
                                    保存
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
