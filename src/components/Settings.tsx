/**
 * 设置页面组件：配置API密钥等设置
 * 
 * 遵循 docs/ARCHITECTURE.md 中的UI组件规范
 * 已进入 Phase 11: 中文国际化回归与返回按钮样式修整
 */

import React, { useState, useEffect, useRef } from "react";
import { AppConfig, AIProvider } from "../types";
import { saveConfig } from "../utils/tauri";

interface SettingsProps {
  config: AppConfig | null;
  onConfigChange: () => void;
  onBack?: () => void;
}

/**
 * 设置页面组件 - 采用黑白极简风 (Monochrome)
 * 纯净中文界面，无分割线，居中返回按钮
 */
export const Settings: React.FC<SettingsProps> = ({
  config,
  onConfigChange,
  onBack,
}) => {
  const [formData, setFormData] = useState<AppConfig>({
    provider: "claude",
    api_key: "",
    model: "claude-3-5-sonnet-20241022",
    sandbox_path: "",
    auto_confirm: false,
    log_level: "INFO",
    email_sender: "",
    email_password: "",
    email_smtp_server: "smtp.gmail.com",
    email_smtp_port: 587,
    email_imap_server: "imap.gmail.com",
    email_imap_port: 993,
  });

  const [activeTab, setActiveTab] = useState<"ai" | "email" | "system">("ai");
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // 各提供商的模型列表
  const providerModels: Record<AIProvider, string[]> = {
    claude: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    anthropic: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    openai: ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
    deepseek: ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
    grok: ["grok-beta"],
  };

  useEffect(() => {
    if (config) {
      setFormData({
        ...config,
        email_sender: config.email_sender || "",
        email_password: config.email_password || "",
        email_smtp_server: config.email_smtp_server || "smtp.gmail.com",
        email_smtp_port: config.email_smtp_port || 587,
        email_imap_server: config.email_imap_server || "imap.gmail.com",
        email_imap_port: config.email_imap_port || 993,
      });
    }
  }, [config]);

  // 处理点击外部自动关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setModelDropdownOpen(false);
      }
    };

    if (modelDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    } else {
      document.removeEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [modelDropdownOpen]);

  const handleProviderChange = (provider: AIProvider) => {
    const defaultModel = providerModels[provider][0];
    setFormData((prev) => ({
      ...prev,
      provider,
      model: defaultModel,
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      await saveConfig(formData);
      setSaveSuccess(true);
      setMessage(null);
      onConfigChange();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      setMessage({
        type: "error",
        text: `保存失败: ${error instanceof Error ? error.message : "未知错误"}`,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (
    field: keyof AppConfig,
    value: string | boolean | number
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const renderSidebarItem = (id: typeof activeTab, label: string, icon: React.ReactNode) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-2xl transition-all ${activeTab === id
        ? "bg-black dark:bg-white text-white dark:text-black font-bold shadow-xl shadow-black/10 dark:shadow-white/5"
        : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50"
        }`}
    >
      <div className={activeTab === id ? "scale-110" : "opacity-80"}>
        {icon}
      </div>
      <span className="text-sm tracking-tight">{label}</span>
    </button>
  );

  return (
    <div className="h-full flex flex-col bg-white dark:bg-[#0a0a0a] text-gray-900 dark:text-gray-100 font-sans transition-colors duration-300">
      {/* Header - 纯净布局 */}
      <div className="flex items-center justify-between px-10 py-6 bg-transparent z-10">
        <div className="flex items-center gap-8">
          {onBack && (
            <button
              onClick={onBack}
              className="group w-12 h-12 flex items-center justify-center rounded-2xl bg-black dark:bg-white text-white dark:text-black transition-all hover:scale-105 active:scale-95 shadow-lg shadow-black/10 dark:shadow-white/5"
              title="返回首页"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 18l-6-6 6-6" />
              </svg>
            </button>
          )}
          <div>
            <h2 className="text-xl font-black tracking-tighter">设置</h2>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-8 h-1 bg-black dark:bg-white rounded-full" />
              <p className="text-[10px] font-black uppercase tracking-[0.4em] text-gray-400 dark:text-gray-500">System Preferences</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {message?.type === "error" && (
            <div className="animate-in fade-in slide-in-from-right-4 text-[10px] font-black uppercase tracking-widest px-8 py-3.5 rounded-full flex items-center gap-3 bg-red-500 text-white shadow-xl shadow-red-500/20">
              {message.text}
            </div>
          )}
          <button
            onClick={handleSave}
            disabled={saving || !formData.api_key}
            className={`flex items-center gap-3 px-8 py-3 rounded-full font-black text-[10px] uppercase tracking-[0.2em] shadow-2xl transition-all active:scale-[0.95] hover:opacity-90 disabled:opacity-20 ${saveSuccess
              ? "bg-green-500 text-white shadow-green-500/20"
              : "bg-black dark:bg-white text-white dark:text-black shadow-black/20 dark:shadow-white/10"
              }`}
          >
            {saving ? (
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : saveSuccess ? (
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
                配置已保存
              </div>
            ) : "保存更改"}
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - 背景色与全局一致 */}
        <div className="w-64 p-8 space-y-4 overflow-y-auto mt-4 px-10">
          <div className="px-5 mb-8">
            <div className="text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.4em] mb-1">导航菜单</div>
          </div>

          <div className="space-y-4">
            {renderSidebarItem("ai", "AI 模型配置", (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            ))}
            {renderSidebarItem("email", "邮件服务集成", (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            ))}
            {renderSidebarItem("system", "系统与环境", (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
            ))}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-12">
          <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-12 duration-1000">
            {activeTab === "ai" && (
              <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
                <header className="mb-12">
                  <h3 className="text-xl font-black mb-2 tracking-tighter uppercase">AI 模型核心</h3>
                  <p className="text-gray-600 dark:text-gray-300 font-medium text-xs leading-relaxed max-w-sm">
                    配置推动您自动化流程的智能大脑内核。
                  </p>
                </header>

                <div className="space-y-10">
                  <section className="space-y-6">
                    <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-4">模型服务商</label>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 max-w-sm">
                      {(["claude", "openai", "deepseek", "grok"] as AIProvider[]).map((p) => (
                        <button
                          key={p}
                          onClick={() => handleProviderChange(p)}
                          className={`group relative flex flex-col items-center justify-center p-2.5 rounded-xl border-2 transition-all duration-300 ${formData.provider === p
                            ? "border-black dark:border-white bg-black dark:bg-white text-white dark:text-black shadow-lg"
                            : "border-transparent bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700"
                            }`}
                        >
                          <span className="capitalize font-black text-[10px] tracking-widest">{p}</span>
                        </button>
                      ))}
                    </div>
                  </section>

                  <div className="max-w-2xl">
                    <div className="flex items-center justify-between mb-8 px-5">
                      <label className="text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em]">API 凭证 (API Key)</label>
                      <a
                        href={
                          formData.provider === "claude" ? "https://console.anthropic.com/" :
                            formData.provider === "openai" ? "https://platform.openai.com/api-keys" :
                              formData.provider === "deepseek" ? "https://platform.deepseek.com/api_keys" : "https://x.ai/api"
                        }
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-gray-400 hover:text-black dark:hover:text-white font-black transition-colors underline decoration-2 underline-offset-4"
                      >获取密钥 ↗</a>
                    </div>
                    <input
                      type="password"
                      value={formData.api_key}
                      onChange={(e) => handleChange("api_key", e.target.value)}
                      placeholder="请输入您的身份验证令牌"
                      className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all font-mono text-xs tracking-[0.1em]"
                    />
                  </div>

                  <div className="relative max-w-2xl" ref={dropdownRef}>
                    <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] mb-8 px-5">选择模型</label>
                    <div className="relative">
                      <div
                        onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                        className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 rounded-2xl cursor-pointer transition-all flex items-center justify-between group"
                      >
                        <span className="font-black text-xs uppercase tracking-widest">{formData.model}</span>
                        <svg
                          className={`w-5 h-5 transition-transform duration-300 ${modelDropdownOpen ? "rotate-180" : ""}`}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </div>

                      {modelDropdownOpen && (
                        <>
                          <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-gray-900 border-2 border-black dark:border-white rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-200 origin-top">
                            <div className="max-h-48 overflow-y-auto custom-scrollbar">
                              {providerModels[formData.provider]?.map((m) => (
                                <div
                                  key={m}
                                  onClick={() => {
                                    handleChange("model", m);
                                    setModelDropdownOpen(false);
                                  }}
                                  className={`px-6 py-3.5 text-xs font-black uppercase tracking-widest cursor-pointer transition-colors ${formData.model === m
                                    ? "bg-black dark:bg-white text-white dark:text-black"
                                    : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
                                    }`}
                                >
                                  {m}
                                </div>
                              ))}
                            </div>
                          </div>
                          <style>{`
                              .custom-scrollbar::-webkit-scrollbar {
                                width: 4px;
                              }
                              .custom-scrollbar::-webkit-scrollbar-track {
                                background: transparent;
                              }
                              .custom-scrollbar::-webkit-scrollbar-thumb {
                                background: currentColor;
                                border-radius: 2px;
                                opacity: 0.2;
                              }
                            `}</style>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "email" && (
              <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
                <header className="mb-12">
                  <h3 className="text-xl font-black mb-2 tracking-tighter uppercase">邮件集成服务</h3>
                  <p className="text-gray-600 dark:text-gray-300 font-medium text-xs leading-relaxed max-w-sm">
                    配置 SMTP 服务以实现自动化任务的邮件通知与集成。
                  </p>
                </header>

                <div className="space-y-12">
                  <section className="space-y-6">
                    <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">快捷配置 (Quick Config)</label>
                    <div className="grid grid-cols-3 gap-3 max-w-sm">
                      {[
                        { label: "Gmail", server: "smtp.gmail.com", port: 587 },
                        { label: "QQ 邮箱", server: "smtp.qq.com", port: 587 },
                        { label: "Outlook", server: "smtp.office365.com", port: 587 },
                      ].map((preset) => (
                        <button
                          key={preset.label}
                          onClick={() => {
                            handleChange("email_smtp_server", preset.server);
                            handleChange("email_smtp_port", preset.port);
                            // 自动推断 IMAP
                            if (preset.label === "Gmail") {
                              handleChange("email_imap_server", "imap.gmail.com");
                              handleChange("email_imap_port", 993);
                            } else if (preset.label === "QQ 邮箱") {
                              handleChange("email_imap_server", "imap.qq.com");
                              handleChange("email_imap_port", 993);
                            } else if (preset.label === "Outlook") {
                              handleChange("email_imap_server", "outlook.office365.com");
                              handleChange("email_imap_port", 993);
                            }
                          }}
                          className={`py-3 rounded-xl text-[10px] font-black tracking-widest transition-all border-2 ${formData.email_smtp_server === preset.server
                            ? "bg-black dark:bg-white text-white dark:text-black border-black dark:border-white shadow-lg"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-500 border-transparent hover:bg-gray-200 dark:hover:bg-gray-700 font-medium"
                            }`}
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </section>

                  <div className="grid grid-cols-2 gap-8 max-w-2xl">
                    <div className="space-y-6">
                      <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">SMTP 服务器 (发件)</label>
                      <input
                        type="text"
                        value={formData.email_smtp_server || ""}
                        onChange={(e) => handleChange("email_smtp_server", e.target.value)}
                        placeholder="例如: smtp.gmail.com"
                        className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all text-xs font-black tracking-widest"
                      />
                    </div>
                    <div className="space-y-6">
                      <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">SMTP 端口</label>
                      <input
                        type="number"
                        value={formData.email_smtp_port || 587}
                        onChange={(e) => handleChange("email_smtp_port", parseInt(e.target.value) || 587)}
                        className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all text-xs font-black"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-8 max-w-2xl">
                    <div className="space-y-6">
                      <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">IMAP 服务器 (收件)</label>
                      <input
                        type="text"
                        value={formData.email_imap_server || ""}
                        onChange={(e) => handleChange("email_imap_server", e.target.value)}
                        placeholder="例如: imap.gmail.com"
                        className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all text-xs font-black tracking-widest"
                      />
                    </div>
                    <div className="space-y-6">
                      <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">IMAP 端口</label>
                      <input
                        type="number"
                        value={formData.email_imap_port || 993}
                        onChange={(e) => handleChange("email_imap_port", parseInt(e.target.value) || 993)}
                        className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all text-xs font-black"
                      />
                    </div>
                  </div>

                  <div className="space-y-6 max-w-2xl">
                    <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">发件人账号</label>
                    <input
                      type="email"
                      value={formData.email_sender || ""}
                      onChange={(e) => handleChange("email_sender", e.target.value)}
                      placeholder="您的邮箱地址"
                      className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all text-xs font-black tracking-widest"
                    />
                  </div>

                  <div className="space-y-6 max-w-2xl">
                    <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">应用专用密码 (App Password)</label>
                    <input
                      type="password"
                      value={formData.email_password || ""}
                      onChange={(e) => handleChange("email_password", e.target.value)}
                      placeholder="请输入 16 位专用密码"
                      className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all text-xs font-black tracking-widest"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === "system" && (
              <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
                <header className="mb-8">
                  <h3 className="text-xl font-black mb-2 tracking-tighter uppercase">系统运行环境</h3>
                  <p className="text-gray-600 dark:text-gray-300 font-medium text-xs leading-relaxed max-w-sm">
                    定义系统行为偏好、安全沙盒路径以及调试信息详略。
                  </p>
                </header>

                <div className="space-y-10">
                  <section className="space-y-6">
                    <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">沙盒根路径 (Sandbox Root)</label>
                    <input
                      type="text"
                      value={formData.sandbox_path}
                      onChange={(e) => handleChange("sandbox_path", e.target.value)}
                      placeholder="~/.deskjarvis/sandbox"
                      className="w-full px-6 py-4 bg-gray-100 dark:bg-gray-800/50 border-none rounded-2xl focus:ring-4 focus:ring-black/5 dark:focus:ring-white/5 outline-none transition-all font-mono text-xs tracking-[0.1em]"
                    />
                  </section>

                  <section className="p-5 rounded-2xl bg-gray-50/50 dark:bg-gray-900/10 transition-all border border-gray-100 dark:border-gray-800/50">
                    <div className="flex items-center justify-between gap-8">
                      <div className="max-w-md">
                        <div className="text-sm font-black uppercase tracking-widest mb-1">完全自动化模式</div>
                        <div className="text-[10px] text-gray-600 dark:text-gray-400 font-medium uppercase tracking-widest opacity-90">允许 Agent 在简单任务中自动做出决策。</div>
                      </div>
                      <button
                        onClick={() => handleChange("auto_confirm", !formData.auto_confirm)}
                        className={`shrink-0 w-12 h-7 rounded-full p-1 transition-all duration-500 ${formData.auto_confirm ? "bg-black dark:bg-white" : "bg-gray-200 dark:bg-gray-800"}`}
                      >
                        <div className={`w-5 h-5 rounded-full shadow-lg transition-all duration-500 ${formData.auto_confirm ? "translate-x-5 bg-white dark:bg-black" : "translate-x-0 bg-white"}`} />
                      </button>
                    </div>
                  </section>

                  <section className="space-y-6">
                    <label className="block text-[10px] font-black text-gray-600 dark:text-gray-300 uppercase tracking-[0.5em] px-5">系统日志级别</label>
                    <div className="grid grid-cols-4 gap-4">
                      {["DEBUG", "INFO", "WARNING", "ERROR"].map((level) => (
                        <button
                          key={level}
                          onClick={() => handleChange("log_level", level)}
                          className={`py-3 rounded-2xl text-[9px] font-black tracking-[0.3em] transition-all border-2 ${formData.log_level === level
                            ? "bg-black dark:bg-white text-white dark:text-black border-black dark:border-white shadow-xl"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-400 border-transparent hover:text-gray-600"
                            }`}
                        >
                          {level}
                        </button>
                      ))}
                    </div>
                  </section>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
