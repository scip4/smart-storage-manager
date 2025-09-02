import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { HardDrive, Trash2, Archive, Play, Settings, AlertTriangle, Film, Tv, ExternalLink, Check, X, RefreshCw, FileText, Search, BarChart3, Shield, Zap } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5001/api';
const ITEMS_PER_PAGE = 10;

// --- Helper Functions & Components ---

const formatStorage = (gb) => {
  if (gb >= 1000) {
    return (gb / 1000).toFixed(1) + ' TB';
  }
  return (gb || 0).toFixed(1) + ' GB';
};

const LoadingSpinner = () => (
  <div className="flex justify-center items-center p-12">
    <div className="relative">
      <div className="w-12 h-12 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
      <div className="absolute inset-0 w-12 h-12 border-4 border-transparent border-r-blue-300 rounded-full animate-spin animate-reverse"></div>
    </div>
    <span className="ml-4 text-lg font-medium text-slate-700">Loading data...</span>
  </div>
);

const ErrorDisplay = ({ error, onRetry }) => (
    <div className="bg-gradient-to-br from-red-50 to-red-100 border border-red-200 rounded-xl p-8 text-center shadow-lg">
      <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="w-8 h-8 text-white" />
      </div>
      <h3 className="text-xl font-bold text-red-900 mb-2">Connection Error</h3>
      <p className="text-red-700 mb-6 max-w-md mx-auto">{error || "Unable to connect to the backend service. Please check your connection."}</p>
      <button
        onClick={onRetry}
        className="px-6 py-3 bg-red-500 text-white font-semibold rounded-lg hover:bg-red-600 transition-all duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
      >
        Try Again
      </button>
    </div>
);

const InputField = React.memo(({ label, value, onChange, type = "text", placeholder = "" }) => (
    <div className="space-y-2">
        <label className="block text-sm font-semibold text-slate-700">{label}</label>
        <input 
          type={type} 
          value={value || ''} 
          onChange={onChange} 
          className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white shadow-sm hover:shadow-md" 
          placeholder={placeholder} 
        />
    </div>
));

const ArchiveFolderInput = React.memo(({ folder, index, onUpdate, onDelete }) => (
    <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
        <input 
          type="text" 
          value={folder} 
          onChange={(e) => onUpdate(index, e.target.value)} 
          className="flex-1 px-3 py-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white" 
        />
        <button 
          onClick={() => onDelete(index)} 
          className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-md transition-colors duration-200"
        >
          <X className="w-4 h-4" />
        </button>
    </div>
));

const StatCard = ({ icon: Icon, title, value, subtitle, color = "blue", onClick, clickable = false }) => (
  <div 
    className={`bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-all duration-300 border border-slate-100 ${clickable ? 'cursor-pointer hover:scale-105 hover:border-blue-200' : ''}`}
    onClick={onClick}
  >
    <div className="flex items-center justify-between">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">{title}</h3>
        <p className={`text-3xl font-bold text-${color}-600`}>{value}</p>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      <div className={`p-4 bg-${color}-100 rounded-xl`}>
        <Icon className={`w-8 h-8 text-${color}-600`} />
      </div>
    </div>
    {clickable && (
      <div className="mt-4 text-xs text-blue-600 font-medium"></div>
    )}
  </div>
);

const ActionButton = ({ onClick, variant = "primary", size = "md", children, disabled = false, icon: Icon }) => {
  const variants = {
    primary: "bg-blue-500 hover:bg-blue-600 text-white shadow-md hover:shadow-lg",
    secondary: "bg-slate-100 hover:bg-slate-200 text-slate-700 shadow-sm hover:shadow-md",
    danger: "bg-red-500 hover:bg-red-600 text-white shadow-md hover:shadow-lg",
    success: "bg-green-500 hover:bg-green-600 text-white shadow-md hover:shadow-lg",
    archive: "bg-indigo-500 hover:bg-indigo-600 text-white shadow-md hover:shadow-lg"
  };
  
  const sizes = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base"
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        ${variants[variant]} 
        ${sizes[size]} 
        font-semibold rounded-lg transition-all duration-200 transform hover:-translate-y-0.5 
        disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
        flex items-center space-x-2
      `}
    >
      {Icon && <Icon className="w-4 h-4" />}
      <span>{children}</span>
    </button>
  );
};

const LogViewer = () => {
  const [logs, setLogs] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/logs`);
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      setLogs("Failed to load logs. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-100">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-slate-800 flex items-center">
          <div className="p-2 bg-slate-100 rounded-lg mr-3">
            <FileText className="w-6 h-6 text-slate-600" />
          </div>
          Application Logs
        </h2>
        <ActionButton
          onClick={fetchLogs}
          disabled={loading}
          variant="secondary"
          icon={RefreshCw}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </ActionButton>
      </div>
      <div className="bg-slate-900 text-green-400 font-mono text-sm rounded-xl p-6 h-96 overflow-y-scroll shadow-inner border border-slate-700">
        <pre className="whitespace-pre-wrap">
          {loading ? 'Loading logs...' : logs}
        </pre>
      </div>
      <p className="text-xs text-slate-500 mt-3">Displaying the last 200 lines of the log file.</p>
    </div>
  );
};

const MediaItemCard = ({ item, onRuleChange, onExecuteAction }) => {
    const isCandidate = item.status ? item.status.includes('candidate') : false;

    return (
        <div className={`bg-white rounded-xl p-6 border transition-all duration-300 hover:shadow-lg ${isCandidate ? 'border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50' : 'border-slate-200 hover:border-slate-300'}`}>
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center space-y-4 lg:space-y-0">
                <div className="flex-1 space-y-3">
                    <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-lg ${item.type === 'movie' ? 'bg-purple-100' : 'bg-blue-100'}`}>
                            {item.type === 'movie' ? 
                                <Film className="w-5 h-5 text-purple-600" /> : 
                                <Tv className="w-5 h-5 text-blue-600" />
                            }
                        </div>
                        <div>
                            <h3 className="font-bold text-slate-800 text-lg">{item.title}</h3>
                            {item.year && <span className="text-slate-500 text-sm">({item.year})</span>}
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                        <div className="flex flex-col">
                            <span className="font-semibold text-slate-600">Size</span>
                            <span className="text-slate-800">{item.size} GB</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="font-semibold text-slate-600">Last Watched</span>
                            <span className="text-slate-800">{item.lastWatched || 'Never'}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="font-semibold text-slate-600">Watch Count</span>
                            <span className="text-slate-800">{item.watchCount}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="font-semibold text-slate-600">Status</span>
                            <span className={`font-medium ${isCandidate ? 'text-amber-700' : 'text-green-700'}`}>
                                {item.status}
                            </span>
                        </div>
                    </div>
                    
                    {item.streamingServices && (
                        <div className="bg-slate-50 rounded-lg p-3">
                            <span className="text-sm font-semibold text-slate-600">Available on: </span>
                            <span className="text-sm text-slate-700">{item.streamingServices}</span>
                        </div>
                    )}
                </div>
                
                <div className="flex items-center space-x-3 lg:ml-6">
                    <select
                        value={item.rule || ''}
                        onChange={(e) => onRuleChange(item.id, e.target.value)}
                        className="px-3 py-2 border border-slate-200 rounded-lg bg-white text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                        <option value="auto-manage">Auto Manage</option>
                        <option value="keep-forever">Keep Forever</option>
                        <option value="archive-after-6months">Archive After 6 Months</option>
                        <option value="delete-after-watched">Delete After Watched</option>
                    </select>
                    <ActionButton onClick={() => onExecuteAction(item, 'archive')} variant="archive" size="sm" icon={Archive}>
                        Archive
                    </ActionButton>
                    <ActionButton onClick={() => onExecuteAction(item, 'delete')} variant="danger" size="sm" icon={Trash2}>
                        Delete
                    </ActionButton>
                </div>
            </div>
        </div>
    );
};

// --- VIEW COMPONENTS ---

const Dashboard = React.memo(({ loading, error, onOpenStreamingModal, storageData, archiveData, potentialSavings, libraryStats, candidates, executeAction, onRetry }) => {
    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorDisplay error={error} onRetry={onRetry} />;
    
    return (
        <div className="space-y-8">
            {/* Storage Overview */}
            <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-100">
                <div className="flex items-center mb-6">
                    <div className="p-3 bg-blue-100 rounded-xl mr-4">
                        <HardDrive className="w-8 h-8 text-blue-600" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-slate-800">Storage Overview</h2>
                        <p className="text-slate-600">Monitor your media storage utilization</p>
                    </div>
                </div>
                
                <div className="grid grid-cols-2 lg:grid-cols-6 gap-6">
                    <StatCard
                        icon={BarChart3}
                        title="Main Used"
                        value={formatStorage(storageData.used)}
                        color="blue"
                    />
                    <StatCard
                        icon={HardDrive}
                        title="Main Available"
                        value={formatStorage(storageData.available)}
                        color="green"
                    />
                    <StatCard
                        icon={Zap}
                        title="Potential Savings"
                        value={formatStorage(potentialSavings)}
                        color="orange"
                    />
                    <StatCard
                        icon={Archive}
                        title="Archive Total"
                        value={formatStorage(archiveData.total)}
                        color="slate"
                    />
                    <StatCard
                        icon={Archive}
                        title="Archive Used"
                        value={formatStorage(archiveData.used)}
                        color="purple"
                    />
                    <StatCard
                        icon={Archive}
                        title="Archive Available"
                        value={formatStorage(archiveData.available)}
                        color="indigo"
                    />
                </div>
            </div>

            {/* Library Stats */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <StatCard
                    icon={Tv}
                    title="TV Shows"
                    value={`${libraryStats.tv || 0} Series`}
                    subtitle={`${libraryStats.tv_episodes || 0} Episodes • ${formatStorage(libraryStats.tv_size)}`}
                    color="blue"
                />
                <StatCard
                    icon={Film}
                    title="Movies"
                    value={libraryStats.movies || 0}
                    subtitle={formatStorage(libraryStats.movies_size)}
                    color="purple"
                />
                <StatCard
                    icon={ExternalLink}
                    title="On Streaming"
                    value={libraryStats.onStreaming || 0}
                    subtitle="Click to view details"
                    color="green"
                    onClick={onOpenStreamingModal}
                    clickable={true}
                />
            </div>

            {/* Recommended Actions */}
            <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-100">
                <div className="flex items-center mb-6">
                    <div className="p-3 bg-amber-100 rounded-xl mr-4">
                        <Shield className="w-8 h-8 text-amber-600" />
                    </div>
                    <div>
                        <h3 className="text-2xl font-bold text-slate-800">Recommended Actions</h3>
                        <p className="text-slate-600">Smart suggestions to optimize your storage</p>
                    </div>
                </div>
                
                <div className="space-y-4 max-h-96 overflow-y-auto">
                    {candidates.length > 0 ? candidates.map((item, index) => (
                        <div key={`${item.type}-${item.id}-${index}`} className="flex justify-between items-center p-4 bg-slate-50 rounded-xl border border-slate-200 hover:bg-slate-100 transition-colors duration-200">
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center space-x-3">
                                    <div className={`p-2 rounded-lg ${item.type === 'movie' ? 'bg-purple-100' : 'bg-blue-100'}`}>
                                        {item.type === 'movie' ? 
                                            <Film className="w-4 h-4 text-purple-600" /> : 
                                            <Tv className="w-4 h-4 text-blue-600" />
                                        }
                                    </div>
                                    <h4 className="font-semibold text-slate-800">{item.title}</h4>
                                </div>
                                <div className="text-sm text-slate-600 space-y-1">
                                    <p><span className="font-medium">Size:</span> {item.size} GB • <span className="font-medium">Reason:</span> {item.reason}</p>
                                    <p className="text-xs text-slate-500 font-mono">{item.filePath}</p>
                                    {item.streamingServices && (
                                        <p className="text-xs"><span className="font-medium">Streaming:</span> {item.streamingServices}</p>
                                    )}
                                </div>
                            </div>
                            <div className="flex space-x-3 ml-6">
                                {item.status.includes('delete') && (
                                    <ActionButton onClick={() => executeAction(item, 'delete')} variant="danger" size="sm" icon={Trash2}>
                                        Delete
                                    </ActionButton>
                                )}
                                {item.status.includes('archive') && (
                                    <ActionButton onClick={() => executeAction(item, 'archive')} variant="archive" size="sm" icon={Archive}>
                                        Archive
                                    </ActionButton>
                                )}
                            </div>
                        </div>
                    )) : (
                        <div className="text-center py-12">
                            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Check className="w-8 h-8 text-green-600" />
                            </div>
                            <h4 className="text-lg font-semibold text-slate-700 mb-2">All optimized!</h4>
                            <p className="text-slate-500">No cleanup actions needed at this time.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
});

const ContentManagement = React.memo(({ loading, error, allContent, executeAction, onRetry }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [contentFilter, setContentFilter] = useState('all');
    const [sortBy, setSortBy] = useState('size-desc');
    const [currentPage, setCurrentPage] = useState(1);

    const processedContent = useMemo(() => {
        let filtered = allContent || [];
        if (contentFilter === 'tv') filtered = filtered.filter(item => item.type === 'tv');
        if (contentFilter === 'movies') filtered = filtered.filter(item => item.type === 'movie');
        if (searchTerm) { filtered = filtered.filter(item => item.title.toLowerCase().includes(searchTerm.toLowerCase())); }
        filtered.sort((a, b) => { const [field, dir] = sortBy.split('-'); const mod = dir === 'asc' ? 1 : -1; if (field === 'title') return a.title.localeCompare(b.title) * mod; if (field === 'size') return (a.size - b.size) * mod; return 0; });
        return filtered;
    }, [allContent, contentFilter, searchTerm, sortBy]);

    const totalPages = Math.ceil(processedContent.length / ITEMS_PER_PAGE);
    const paginatedItems = processedContent.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

    useEffect(() => { setCurrentPage(1); }, [contentFilter, searchTerm, sortBy]);

    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorDisplay error={error} onRetry={onRetry} />;

    return (
        <div className="space-y-6">
            {/* Search and Filter Bar */}
            <div className="bg-white rounded-xl shadow-md p-6 border border-slate-100">
                <div className="flex flex-col lg:flex-row gap-4 items-center">
                    <div className="relative flex-grow">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                        <input 
                            type="text" 
                            placeholder="Search by title..." 
                            value={searchTerm} 
                            onChange={(e) => setSearchTerm(e.target.value)} 
                            className="w-full pl-12 pr-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-50" 
                        />
                    </div>
                    <div className="flex gap-3">
                        <select 
                            value={contentFilter} 
                            onChange={(e) => setContentFilter(e.target.value)} 
                            className="px-4 py-3 border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent font-medium"
                        >
                            <option value="all">All Content</option>
                            <option value="tv">TV Shows</option>
                            <option value="movies">Movies</option>
                        </select>
                        <select 
                            value={sortBy} 
                            onChange={(e) => setSortBy(e.target.value)} 
                            className="px-4 py-3 border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent font-medium"
                        >
                            <option value="size-desc">Size (High to Low)</option>
                            <option value="size-asc">Size (Low to High)</option>
                            <option value="title-asc">Title (A to Z)</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Content List */}
            <div className="space-y-4">
                {paginatedItems.length > 0 ? paginatedItems.map((item, index) => (
                    <MediaItemCard key={`${item.type}-${item.id}-${index}`} item={item} onRuleChange={() => {}} onExecuteAction={executeAction} />
                )) : (
                    <div className="text-center py-16 bg-white rounded-xl shadow-md border border-slate-100">
                        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Search className="w-8 h-8 text-slate-400" />
                        </div>
                        <h3 className="text-xl font-semibold text-slate-700 mb-2">No content found</h3>
                        <p className="text-slate-500">Try adjusting your search criteria</p>
                    </div>
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex justify-between items-center bg-white rounded-xl shadow-md p-6 border border-slate-100">
                    <ActionButton 
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))} 
                        disabled={currentPage === 1} 
                        variant="secondary"
                    >
                        Previous
                    </ActionButton>
                    <span className="text-sm font-medium text-slate-600">
                        Page {currentPage} of {totalPages}
                    </span>
                    <ActionButton 
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} 
                        disabled={currentPage === totalPages} 
                        variant="secondary"
                    >
                        Next
                    </ActionButton>
                </div>
            )}
        </div>
    );
});

const SettingsPanel = React.memo(({ loading, error, connectionStatus, 
    formSettings, onFieldChange, onAddFolder, onUpdateFolder, onDeleteFolder, 
    onSave, onRetry, onStreamingProviderChange, onAddMapping, onUpdateMapping, 
    onDeleteMapping, handleManualCleanup, isCleaningUp, cleanupMessage, 
    sonarrRootFolders, radarrRootFolders }) => {
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState('');

    const handleManualSync = async () => {
        setIsSyncing(true);
        setSyncMessage('');
        try {
            const response = await fetch(`${API_BASE_URL}/sync/trigger`, { method: 'POST' });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Failed to start sync.');
            }
            
            setSyncMessage(data.message);
            setTimeout(() => setSyncMessage(''), 5000);

        } catch (err) {
            setSyncMessage(`Error: ${err.message}`);
        } finally {
            setTimeout(() => setIsSyncing(false), 3000);
        }
    };    
    
    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorDisplay error={error} onRetry={onRetry} />;
    
        // Filter mappings by type for separate rendering
    const tvMappings = (formSettings.archiveMappings || []).filter(m => m.type === 'tv');
    const movieMappings = (formSettings.archiveMappings || []).filter(m => m.type === 'movie');

    return (
        <div className="space-y-8">
            {/* Connection Status */}
            <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-100">
                <div className="flex items-center mb-6">
                    <div className="p-3 bg-green-100 rounded-xl mr-4">
                        <Shield className="w-8 h-8 text-green-600" />
                    </div>
                    <div>
                        <h3 className="text-2xl font-bold text-slate-800">Connection Status</h3>
                        <p className="text-slate-600">Monitor service connectivity</p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {Object.entries(connectionStatus).map(([service, status]) => (
                        <div key={service} className={`p-6 border-2 rounded-xl transition-all duration-200 ${status === 'Connected' ? 'bg-gradient-to-br from-green-50 to-emerald-50 border-green-200' : 'bg-gradient-to-br from-red-50 to-rose-50 border-red-200'}`}>
                            <div className="flex items-center space-x-3">
                                <div className={`w-3 h-3 rounded-full ${status === 'Connected' ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
                                <div>
                                    <div className="font-bold text-slate-800 text-lg capitalize">{service}</div>
                                    <div className={`text-sm font-medium ${status === 'Connected' ? 'text-green-700' : 'text-red-700'}`}>
                                        {status}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Manual Sync */}
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl shadow-lg p-8 border border-blue-200">
                <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center space-y-4 lg:space-y-0">
                    <div>
                        <h3 className="text-2xl font-bold text-slate-800 mb-2">Manual Data Sync</h3>
                        <p className="text-slate-600 max-w-md">
                            Force refresh all data from Plex, Sonarr, and Radarr services immediately.
                        </p>
                    </div>
                    <ActionButton
                        onClick={handleManualSync}
                        disabled={isSyncing}
                        variant="primary"
                        size="lg"
                        icon={RefreshCw}
                    >
                        {isSyncing ? 'Syncing...' : 'Start Sync'}
                    </ActionButton>
                </div>
                {syncMessage && (
                    <div className={`mt-4 p-4 rounded-lg ${syncMessage.startsWith('Error:') ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-green-100 text-green-700 border border-green-200'}`}>
                        <p className="font-medium">{syncMessage}</p>
                    </div>
                )}
            </div>
                        <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4">Automation Settings</h3>
                <div className="space-y-4">
                    <div className="p-4 bg-yellow-50 border-l-4 border-yellow-400">
                        <div className="flex">
                            <div className="flex-shrink-0"><AlertTriangle className="h-5 w-5 text-yellow-400" /></div>
                            <div className="ml-3"><p className="text-sm text-yellow-700"><strong>Warning:</strong> Enabling this will allow the system to automatically delete and archive media from your library based on your rules. Please review your rules carefully.</p></div>
                        </div>
                    </div>

                    <label className="flex items-center space-x-3 cursor-pointer">
                        <input
                            type="checkbox"
                            className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            checked={formSettings.enableAutoActions || false}
                            onChange={(e) => onFieldChange('enableAutoActions', false, e.target.checked)}
                        />
                        <span className="font-medium text-gray-700">Enable Automatic Actions</span>
                    </label>

                    <div className="pt-4 border-t">
                        <button
                            onClick={handleManualCleanup}
                            disabled={isCleaningUp}
                            className="px-6 py-2 bg-orange-500 text-white font-semibold rounded-lg shadow-md hover:bg-orange-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
                        >
                            <Trash2 className={`w-5 h-5 mr-2 ${isCleaningUp ? 'animate-spin' : ''}`} />
                            {isCleaningUp ? 'Cleaning Up...' : 'Run Cleanup Now'}
                        </button>
                        {cleanupMessage && (
                            <p className={`text-sm mt-3 text-center p-2 rounded ${cleanupMessage.startsWith('Error:') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                                {cleanupMessage}
                            </p>
                        )}
                    </div>
                </div>
            </div>
            {/* Configuration */}
            <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-100">
                <div className="flex items-center mb-8">
                    <div className="p-3 bg-slate-100 rounded-xl mr-4">
                        <Settings className="w-8 h-8 text-slate-600" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-slate-800">Configuration</h2>
                        <p className="text-slate-600">Application requires restart for changes to take effect</p>
                    </div>
                </div>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Data Update Interval */}
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-slate-800 border-b border-slate-200 pb-3">System Settings</h3>
                        <InputField 
                            label="Update Interval (minutes)" 
                            value={formSettings.DATA_UPDATE_INTERVAL} 
                            onChange={onFieldChange('DATA_UPDATE_INTERVAL')} 
                            placeholder="e.g., 60"
                        />
                    </div>
                    
                    {/* Plex Settings */}
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-slate-800 border-b border-slate-200 pb-3">Plex Configuration</h3>
                        <InputField 
                            label="Plex URL" 
                            value={formSettings.PLEX_URL} 
                            onChange={onFieldChange('PLEX_URL')} 
                            placeholder="http://localhost:32400"
                        />
                        <InputField 
                            label="Plex Token" 
                            type="password" 
                            value={formSettings.PLEX_TOKEN} 
                            onChange={onFieldChange('PLEX_TOKEN')} 
                            placeholder="Your Plex authentication token"
                        />
                    </div>
                    
                    {/* Sonarr Settings */}
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-slate-800 border-b border-slate-200 pb-3">Sonarr Configuration</h3>
                        <InputField 
                            label="Sonarr URL" 
                            value={formSettings.SONARR_URL} 
                            onChange={onFieldChange('SONARR_URL')} 
                            placeholder="http://localhost:8989"
                        />
                        <InputField 
                            label="Sonarr API Key" 
                            type="password" 
                            value={formSettings.SONARR_API_KEY} 
                            onChange={onFieldChange('SONARR_API_KEY')} 
                            placeholder="Your Sonarr API key"
                        />
                    </div>
                    
                    {/* Radarr Settings */}
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-slate-800 border-b border-slate-200 pb-3">Radarr Configuration</h3>
                        <InputField 
                            label="Radarr URL" 
                            value={formSettings.RADARR_URL} 
                            onChange={onFieldChange('RADARR_URL')} 
                            placeholder="http://localhost:7878"
                        />
                        <InputField 
                            label="Radarr API Key" 
                            type="password" 
                            value={formSettings.RADARR_API_KEY} 
                            onChange={onFieldChange('RADARR_API_KEY')} 
                            placeholder="Your Radarr API key"
                        />
                    </div>
                    
                    {/* Other Settings */}
                    <div className="space-y-6">
                        <h3 className="text-xl font-bold text-slate-800 border-b border-slate-200 pb-3">Storage Settings</h3>
                        <InputField 
                            label="Mount Points" 
                            placeholder="/data/media, /data/downloads" 
                            value={formSettings.MOUNT_POINTS?.join(', ') || ''} 
                            onChange={onFieldChange('MOUNT_POINTS', true)} 
                        />
                    </div>
                </div>

                {/* Archive Folders */}
                <div className="mt-12 space-y-8">
                    <div className="flex items-center">
                        <div className="p-3 bg-indigo-100 rounded-xl mr-4">
                            <Archive className="w-8 h-8 text-indigo-600" />
                        </div>
                        <div>
                            <h3 className="text-2xl font-bold text-slate-800">Archive Folders</h3>
                            <p className="text-slate-600">Configure destination paths for archived content</p>
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* TV Archive Folders */}
                        <div className="space-y-4">
                            <div className="flex items-center space-x-2">
                                <Tv className="w-5 h-5 text-blue-600" />
                                <h4 className="text-lg font-bold text-slate-800">TV Shows</h4>
                            </div>
                            <div className="space-y-3">
                                {formSettings.TV_ARCHIVE_FOLDERS?.map((folder, index) => (
                                    <ArchiveFolderInput
                                        key={`tv-${index}`}
                                        folder={folder}
                                        index={index}
                                        onUpdate={(idx, val) => onUpdateFolder('TV_ARCHIVE_FOLDERS', idx, val)}
                                        onDelete={(idx) => onDeleteFolder('TV_ARCHIVE_FOLDERS', idx)}
                                    />
                                ))}
                                {(!formSettings.TV_ARCHIVE_FOLDERS || formSettings.TV_ARCHIVE_FOLDERS.length === 0) && (
                                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-center">
                                        <p className="text-slate-500">No TV archive folders configured</p>
                                    </div>
                                )}
                                <ActionButton
                                    onClick={() => onAddFolder('TV_ARCHIVE_FOLDERS')}
                                    variant="secondary"
                                    size="sm"
                                >
                                    + Add TV Archive Folder
                                </ActionButton>
                            </div>
                        </div>
                        
                        {/* Movie Archive Folders */}
                        <div className="space-y-4">
                            <div className="flex items-center space-x-2">
                                <Film className="w-5 h-5 text-purple-600" />
                                <h4 className="text-lg font-bold text-slate-800">Movies</h4>
                            </div>
                            <div className="space-y-3">
                                {formSettings.MOVIE_ARCHIVE_FOLDERS?.map((folder, index) => (
                                    <ArchiveFolderInput
                                        key={`mv-${index}`}
                                        folder={folder}
                                        index={index}
                                        onUpdate={(idx, val) => onUpdateFolder('MOVIE_ARCHIVE_FOLDERS', idx, val)}
                                        onDelete={(idx) => onDeleteFolder('MOVIE_ARCHIVE_FOLDERS', idx)}
                                    />
                                ))}
                                {(!formSettings.MOVIE_ARCHIVE_FOLDERS || formSettings.MOVIE_ARCHIVE_FOLDERS.length === 0) && (
                                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-center">
                                        <p className="text-slate-500">No movie archive folders configured</p>
                                    </div>
                                )}
                                <ActionButton
                                    onClick={() => onAddFolder('MOVIE_ARCHIVE_FOLDERS')}
                                    variant="secondary"
                                    size="sm"
                                >
                                    + Add Movie Archive Folder
                                </ActionButton>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            
             <div className="bg-white rounded-lg shadow-md p-6">
                {/* ... Header for Archive Path Mappings ... */}
                <div className="mb-8">
                    <h4 className="text-md font-semibold text-gray-800 border-b pb-2 mb-4 flex items-center"><Tv className="w-5 h-5 mr-2 text-blue-500" /> TV (Sonarr) Mappings</h4>
                    <div className="space-y-3">
                        {tvMappings.map((mapping, index) => (
                            <div key={`tv-map-${index}`} className="grid grid-cols-12 gap-4 items-center">
                                <div className="col-span-5">
                                    <select value={mapping.source || ''} onChange={(e) => onUpdateMapping(index, 'source', e.target.value, 'tv')} className="w-full border rounded px-3 py-1.5 bg-white">
                                        <option value="" disabled>Select a Sonarr Root Folder...</option>
                                        {/* --- FIX IS HERE --- */}
                                        {sonarrRootFolders.map(folder => (
                                            <option key={`sonarr-${folder.id}`} value={folder.path}>
                                                {folder.path}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-span-5"><input type="text" placeholder="/path/to/tv-archive" value={mapping.destination || ''} onChange={(e) => onUpdateMapping(index, 'destination', e.target.value, 'tv')} className="w-full border rounded px-3 py-1.5" /></div>
                                <div className="col-span-2 flex justify-end"><button onClick={() => onDeleteMapping(index, 'tv')} className="p-2 text-red-500 hover:bg-red-100 rounded"><Trash2 className="w-4 h-4" /></button></div>
                            </div>
                        ))}
                        <button onClick={() => onAddMapping('tv')} className="mt-2 px-3 py-1 bg-gray-100 text-gray-800 rounded text-sm hover:bg-gray-200">+ Add TV Mapping</button>
                    </div>
                </div>
                <div>
                    <h4 className="text-md font-semibold text-gray-800 border-b pb-2 mb-4 flex items-center"><Film className="w-5 h-5 mr-2 text-purple-500" /> Movie (Radarr) Mappings</h4>
                    <div className="space-y-3">
                        {movieMappings.map((mapping, index) => (
                            <div key={`movie-map-${index}`} className="grid grid-cols-12 gap-4 items-center">
                                <div className="col-span-5">
                                    <select value={mapping.source || ''} onChange={(e) => onUpdateMapping(index, 'source', e.target.value, 'movie')} className="w-full border rounded px-3 py-1.5 bg-white">
                                        <option value="" disabled>Select a Radarr Root Folder...</option>
                                        {/* --- FIX IS HERE --- */}
                                        {radarrRootFolders.map(folder => (
                                            <option key={`radarr-${folder.id}`} value={folder.path}>
                                                {folder.path}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-span-5"><input type="text" placeholder="/path/to/movie-archive" value={mapping.destination || ''} onChange={(e) => onUpdateMapping(index, 'destination', e.target.value, 'movie')} className="w-full border rounded px-3 py-1.5" /></div>
                                <div className="col-span-2 flex justify-end"><button onClick={() => onDeleteMapping(index, 'movie')} className="p-2 text-red-500 hover:bg-red-100 rounded"><Trash2 className="w-4 h-4" /></button></div>
                            </div>
                        ))}
                        <button onClick={() => onAddMapping('movie')} className="mt-2 px-3 py-1 bg-gray-100 text-gray-800 rounded text-sm hover:bg-gray-200">+ Add Movie Mapping</button>
                    </div>
                </div>
            </div>
            
            
            
            {/* Streaming Preferences */}
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl shadow-lg p-8 border border-green-200">
                <div className="flex items-center mb-6">
                    <div className="p-3 bg-green-100 rounded-xl mr-4">
                        <ExternalLink className="w-8 h-8 text-green-600" />
                    </div>
                    <div>
                        <h3 className="text-2xl font-bold text-slate-800">Streaming Preferences</h3>
                        <p className="text-slate-600">Select which streaming services to monitor for content availability</p>
                    </div>
                </div>
                
                <div className="space-y-4">
                    {(formSettings.availableStreamingProviders && formSettings.availableStreamingProviders.length > 0) ? (
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            {formSettings.availableStreamingProviders.map(provider => (
                                <label key={provider} className="flex items-center space-x-3 p-4 bg-white rounded-lg border border-green-200 cursor-pointer hover:bg-green-50 transition-colors duration-200">
                                    <input
                                        type="checkbox"
                                        className="w-5 h-5 rounded border-2 border-green-300 text-green-600 focus:ring-green-500 focus:ring-2"
                                        checked={(formSettings.STREAMING_PROVIDERS || []).includes(provider)}
                                        onChange={(e) => onStreamingProviderChange(provider, e.target.checked)}
                                    />
                                    <span className="font-medium text-slate-700">{provider}</span>
                                </label>
                            ))}
                        </div>
                    ) : (
                        <div className="p-6 bg-white rounded-lg border border-green-200 text-center">
                            <ExternalLink className="w-12 h-12 text-green-400 mx-auto mb-3" />
                            <p className="text-slate-600 font-medium">No streaming providers configured</p>
                            <p className="text-slate-500 text-sm mt-1">Configure providers in your backend environment file</p>
                        </div>
                    )}
                </div>
            </div>
            

            







            {/* Save Button */}
            <div className="flex justify-center">
                <ActionButton
                    onClick={onSave}
                    variant="primary"
                    size="lg"
                    icon={Check}
                >
                    Save All Settings
                </ActionButton>
            </div>
        </div>
    );
});

// Modal Component
const StreamingModal = ({ isOpen, onClose, mediaList }) => {
    if (!isOpen) return null;

    return (
        <div 
            onClick={onClose} 
            className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        >
            <div 
                onClick={(e) => e.stopPropagation()} 
                className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col border border-slate-200"
            >
                <div className="flex justify-between items-center p-8 border-b border-slate-200">
                    <div className="flex items-center">
                        <div className="p-3 bg-green-100 rounded-xl mr-4">
                            <ExternalLink className="w-8 h-8 text-green-600" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-slate-800">Large Media on Streaming</h2>
                            <p className="text-slate-600">Content available on your preferred streaming services</p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose} 
                        className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors duration-200"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>
                
                <div className="p-8 space-y-4 overflow-y-auto">
                    {mediaList && mediaList.length > 0 ? (
                        mediaList.map(item => (
                            <div key={item.id} className="p-6 border border-slate-200 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors duration-200">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center space-x-3">
                                        <div className={`p-2 rounded-lg ${item.title.includes('Movie') ? 'bg-purple-100' : 'bg-blue-100'}`}>
                                            {item.title.includes('Movie') ? 
                                                <Film className="w-5 h-5 text-purple-600" /> : 
                                                <Tv className="w-5 h-5 text-blue-600" />
                                            }
                                        </div>
                                        <h3 className="font-bold text-slate-800 text-lg">{item.title}</h3>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-2xl font-bold text-slate-800">{item.size.toFixed(1)} GB</div>
                                        <div className="text-sm text-slate-500">Storage used</div>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <span className="text-sm font-semibold text-slate-600">Available on:</span>
                                    <div className="flex flex-wrap gap-2">
                                        {item.streamingServices.join(', ').split(', ').map((service, idx) => (
                                            <span key={idx} className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                                                {service}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                 <div className="flex items-center space-x-2">
                                     <span className="text-sm font-semibold text-slate-600">Root Folder:</span>
                                     <div className="flex flex-wrap gap-2">
                                         {item.rootFolderPath ? (
                                             typeof item.rootFolderPath === 'object'
                                                 ? item.rootFolderPath.path
                                                 : item.rootFolderPath
                                         ) : 'N/A'}
                                     </div>
                                 </div>
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-16">
                            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <ExternalLink className="w-8 h-8 text-slate-400" />
                            </div>
                            <h3 className="text-xl font-semibold text-slate-700 mb-2">No streaming content found</h3>
                            <p className="text-slate-500">No large media found on your preferred streaming services</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// Main Component
const SmartStorageManager = () => {
    // --- NEW STATE for root folders ---
    const [sonarrRootFolders, setSonarrRootFolders] = useState([]);
    const [radarrRootFolders, setRadarrRootFolders] = useState([]);

    // --- NEW STATE FOR CLEANUP BUTTON ---
    const [isCleaningUp, setIsCleaningUp] = useState(false);
    const [cleanupMessage, setCleanupMessage] = useState('');
    const [isStreamingModalOpen, setIsStreamingModalOpen] = useState(false);
    const [streamingMediaData, setStreamingMediaData] = useState([]);
    const [storageData, setStorageData] = useState({});
    const [archiveData, setArchiveData] = useState({});
    const [allContent, setAllContent] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [libraryStats, setLibraryStats] = useState({});
    const [settings, setSettings] = useState({});
    const [potentialSavings, setPotentialSavings] = useState(0);
    const [activeTab, setActiveTab] = useState('dashboard');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isArchiveDialogOpen, setIsArchiveDialogOpen] = useState(false);
    const [archiveFolders, setArchiveFolders] = useState([]);
    const [selectedArchiveFolder, setSelectedArchiveFolder] = useState('');
    const [currentArchiveItem, setCurrentArchiveItem] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState({});
    const [formSettings, setFormSettings] = useState({});
    
    useEffect(() => {
        if (Object.keys(settings).length > 0) {
            setFormSettings(settings);
        }
    }, [settings]);

    const fetchDataForTab = useCallback(async (tab) => {
        if (tab === 'logs') return;
        setLoading(true);
        setError(null);
        try {
            let response;
            switch (tab) {
                case 'dashboard':
                    response = await fetch(`${API_BASE_URL}/dashboard`);
                    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
                    const dashData = await response.json();
                    setStorageData(dashData.storageData);
                    setArchiveData(dashData.archiveData);
                    setCandidates(dashData.candidates);
                    setPotentialSavings(dashData.potentialSavings);
                    setLibraryStats(dashData.libraryStats);
                    setStreamingMediaData(dashData.streamingMedia || []);
                    break;
                case 'content':
                    response = await fetch(`${API_BASE_URL}/content`);
                    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
                    setAllContent(await response.json());
                    break;
                case 'settings':
                    const [settingsRes, statusRes, rootFoldersRes] = await Promise.all([
                    fetch(`${API_BASE_URL}/settings`),
                    fetch(`${API_BASE_URL}/status`),
                    fetch(`${API_BASE_URL}/root-folders`)
                    ]);
                    if (!settingsRes.ok || !statusRes.ok || !rootFoldersRes.ok) throw new Error('Failed to fetch settings data.');
                    const settingsData = await settingsRes.json();
                
                    // --- KEY CHANGE: Directly set the formSettings state ---
                    // We no longer need the intermediate 'settings' state variable.
                    setFormSettings(settingsData);
                    //setSettings(await settingsRes.json());
                    setConnectionStatus(await statusRes.json());
                    
                    const rootFoldersData = await rootFoldersRes.json();
                    setSonarrRootFolders(rootFoldersData.sonarr || []);
                    setRadarrRootFolders(rootFoldersData.radarr || []);
                    break;
                default: break;
            }
        } catch (err) { setError(err.message); } finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchDataForTab(activeTab); }, [activeTab, fetchDataForTab]);

    const fetchRootFolders = useCallback(async (type) => {
        try {
            const response = await fetch(`${API_BASE_URL}/root-folders?type=${type}`);
            const data = await response.json();
            if (response.ok) {
                setArchiveFolders(data.folders);
                if (data.folders.length > 0) { setSelectedArchiveFolder(data.folders[0].path); }
            } else { throw new Error(data.message || 'Failed to fetch root folders'); }
        } catch (err) { alert(`Error: ${err.message}`); }
    }, []);

    const openArchiveDialog = useCallback((item) => {
        setCurrentArchiveItem(item);
        setIsArchiveDialogOpen(true);
        fetchRootFolders(item.type === 'tv' ? 'sonarr' : 'radarr');
    }, [fetchRootFolders]);

    const handleOpenStreamingModal = useCallback(() => setIsStreamingModalOpen(true), []);
    const handleCloseStreamingModal = useCallback(() => setIsStreamingModalOpen(false), []);
    
    const handleArchiveConfirm = useCallback(async () => {
        if (!currentArchiveItem || !selectedArchiveFolder) return;
        try {
            const response = await fetch(`${API_BASE_URL}/content/${currentArchiveItem.id}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'archive', item: currentArchiveItem, archivePath: selectedArchiveFolder }),
            });
            const resData = await response.json();
            if (!response.ok) { throw new Error(resData.message || `Failed to perform archive.`); }
            alert(resData.message);
            fetchDataForTab(activeTab);
        } catch (err) { alert(`Error: ${err.message}`); }
        finally { setIsArchiveDialogOpen(false); }
    }, [currentArchiveItem, selectedArchiveFolder, activeTab, fetchDataForTab]);

    const executeAction = useCallback((item, action) => {
        if (action === 'archive') {
            openArchiveDialog(item);
        } else if (action === 'delete') {
            const confirmDelete = window.confirm(`Are you sure you want to delete "${item.title}"? This cannot be undone.`);
            if (confirmDelete) {
                (async () => {
                    try {
                        const response = await fetch(`${API_BASE_URL}/content/${item.id}/action`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, item }), });
                        const resData = await response.json();
                        if (!response.ok) { throw new Error(resData.message || `Failed to perform ${action}.`); }
                        alert(resData.message);
                        fetchDataForTab(activeTab);
                    } catch (err) { alert(`Error: ${err.message}`); }
                })();
            }
        }
    }, [activeTab, fetchDataForTab, openArchiveDialog]);

    //const handleSaveSettings = useCallback(async () => {
    //    try {
    //        const response = await fetch(`${API_BASE_URL}/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formSettings) });
    //        if (!response.ok) { const errorData = await response.json(); throw new Error(errorData.message || 'Failed to save settings.'); }
    //        alert('Settings saved successfully!');
    //        fetchDataForTab('settings');
    //    } catch (err) { alert(`Error: ${err.message}`); }
    //}, [formSettings, fetchDataForTab]);
    
    const handleSaveSettings = useCallback(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formSettings),
            });
            if (!response.ok) { throw new Error('Failed to save settings.'); }
            alert('Settings saved successfully!');
            // Re-fetch to confirm and get any backend-computed values
            fetchDataForTab('settings');
        } catch (err) { alert(`Error: ${err.message}`); }
    }, [formSettings, fetchDataForTab]);



    // --- UPDATED field change handler ---
    const handleFieldChange = useCallback((field, isArray = false, isCheckbox = false) => (e) => {
        const value = isCheckbox ? e.target.checked : (isArray ? e.target.value.split(',').map(s => s.trim()) : e.target.value);
        setFormSettings(prev => ({ ...prev, [field]: value }));
    }, []);

    // --- NEW handler for the manual cleanup button ---
    const handleManualCleanup = useCallback(async () => {
        setIsCleaningUp(true);
        setCleanupMessage('');
        try {
            const response = await fetch(`${API_BASE_URL}/cleanup/trigger`, { method: 'POST' });
            const data = await response.json();
            if (!response.ok) { throw new Error(data.message); }
            setCleanupMessage(data.message);
            setTimeout(() => setCleanupMessage(''), 5000);
        } catch (err) {
            setCleanupMessage(`Error: ${err.message}`);
        } finally {
            setTimeout(() => setIsCleaningUp(false), 3000);
        }
    }, []);

    const handleStreamingProviderChange = useCallback((provider, isChecked) => {
        setFormSettings(prev => {
            const currentServices = prev.STREAMING_PROVIDERS || [];
            let newServices;
            if (isChecked) {
                newServices = [...new Set([...currentServices, provider])];
            } else {
                newServices = currentServices.filter(s => s !== provider);
            }
            return { ...prev, STREAMING_PROVIDERS: newServices };
        });
    }, []);

    const handleAddFolder = useCallback((folderType) => {
        setFormSettings(prev => ({ ...prev, [folderType]: [...(prev[folderType] || []), ''] }));
    }, []);

    const handleUpdateFolder = useCallback((folderType, index, value) => {
        setFormSettings(prev => { const folders = [...(prev[folderType] || [])]; folders[index] = value; return { ...prev, [folderType]: folders }; });
    }, []);

    const handleDeleteFolder = useCallback((folderType, index) => {
        setFormSettings(prev => { const folders = [...(prev[folderType] || [])]; folders.splice(index, 1); return { ...prev, [folderType]: folders }; });
    }, []);


    const handleAddMapping = useCallback((type) => {
        setFormSettings(prev => ({
            ...prev,
            archiveMappings: [...(prev.archiveMappings || []), { source: '', destination: '', type }]
        }));
    }, []);

    const handleUpdateMapping = useCallback((originalIndex, field, value, type) => {
        setFormSettings(prev => {
            const allMappings = [...prev.archiveMappings];
            // Find the true index in the combined array
            let count = -1;
            const trueIndex = allMappings.findIndex(m => {
                if (m.type === type) count++;
                return count === originalIndex;
            });

            if (trueIndex > -1) {
                allMappings[trueIndex] = { ...allMappings[trueIndex], [field]: value };
            }
            return { ...prev, archiveMappings: allMappings };
        });
    }, []);

    const handleDeleteMapping = useCallback((originalIndex, type) => {
        setFormSettings(prev => {
            let count = -1;
            const newMappings = prev.archiveMappings.filter(m => {
                if (m.type === type) {
                    count++;
                    return count !== originalIndex;
                }
                return true;
            });
            return { ...prev, archiveMappings: newMappings };
        });
    }, []);


    const tabs = [
        { id: 'dashboard', name: 'Dashboard', icon: BarChart3 },
        { id: 'content', name: 'Content', icon: Play },
        { id: 'logs', name: 'Logs', icon: FileText },
        { id: 'settings', name: 'Settings', icon: Settings }
    ];

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
            <div className="max-w-7xl mx-auto p-6">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center space-x-4 mb-4">
                        <div className="p-4 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl shadow-lg">
                            <HardDrive className="w-8 h-8 text-white" />
                        </div>
                        <div>
                            <h1 className="text-4x2 font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                                Smart Storage Manager
                            </h1>
                            <p className="text-slate-600 text-lg font-medium">Automated Plex, Sonarr, and Radarr library optimization</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <div className="mb-8">
                    <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-2">
                        <nav className="flex space-x-2">
                            {tabs.map(({ id, name, icon: Icon }) => (
                                <button
                                    key={id}
                                    onClick={() => setActiveTab(id)}
                                    className={`
                                        flex items-center space-x-3 px-6 py-3 rounded-xl font-semibold transition-all duration-200
                                        ${activeTab === id 
                                            ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-md' 
                                            : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
                                        }
                                    `}
                                >
                                    <Icon className="w-5 h-5" />
                                    <span>{name}</span>
                                </button>
                            ))}
                        </nav>
                    </div>
                </div>

                {/* Content */}
                {activeTab === 'dashboard' && (
                    <Dashboard 
                        loading={loading} 
                        error={error} 
                        storageData={storageData} 
                        archiveData={archiveData} 
                        potentialSavings={potentialSavings} 
                        libraryStats={libraryStats} 
                        candidates={candidates} 
                        onOpenStreamingModal={handleOpenStreamingModal} 
                        executeAction={executeAction} 
                        onRetry={() => fetchDataForTab('dashboard')} 
                    />
                )}
                {activeTab === 'content' && (
                    <ContentManagement 
                        loading={loading} 
                        error={error} 
                        allContent={allContent} 
                        executeAction={executeAction} 
                        onRetry={() => fetchDataForTab('content')} 
                    />
                )}
                {activeTab === 'logs' && <LogViewer />}
                {activeTab === 'settings' && (
                    <SettingsPanel
                        loading={loading}
                        error={error}
                        connectionStatus={connectionStatus}
                        formSettings={formSettings}
                        onFieldChange={handleFieldChange}
                        onAddFolder={handleAddFolder}
                        onUpdateFolder={handleUpdateFolder}
                        onDeleteFolder={handleDeleteFolder}
                        onSave={handleSaveSettings}
                        onStreamingProviderChange={handleStreamingProviderChange}
                        onAddMapping={handleAddMapping}
                        onUpdateMapping={handleUpdateMapping}
                        onDeleteMapping={handleDeleteMapping}
                        handleManualCleanup={handleManualCleanup}
                        isCleaningUp={isCleaningUp}
                        cleanupMessage={cleanupMessage}
                        sonarrRootFolders={sonarrRootFolders}
                        radarrRootFolders={radarrRootFolders}
                        onRetry={() => fetchDataForTab('settings')}
                    />
                )}

                {/* Archive Dialog */}
                {isArchiveDialogOpen && (
                    <div className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md border border-slate-200">
                            <div className="p-8">
                                <h2 className="text-2xl font-bold text-slate-800 mb-6">Select Archive Folder</h2>
                                <select 
                                    className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-6 bg-white" 
                                    value={selectedArchiveFolder} 
                                    onChange={(e) => setSelectedArchiveFolder(e.target.value)}
                                >
                                    {archiveFolders.map(folder => (
                                        <option key={folder.path} value={folder.path}>{folder.path}</option>
                                    ))}
                                </select>
                                <div className="flex justify-end space-x-3">
                                    <ActionButton
                                        onClick={() => setIsArchiveDialogOpen(false)}
                                        variant="secondary"
                                    >
                                        Cancel
                                    </ActionButton>
                                    <ActionButton
                                        onClick={handleArchiveConfirm}
                                        variant="archive"
                                        icon={Archive}
                                    >
                                        Archive
                                    </ActionButton>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Streaming Modal */}
                <StreamingModal 
                    isOpen={isStreamingModalOpen} 
                    onClose={handleCloseStreamingModal} 
                    mediaList={streamingMediaData} 
                    handleManualCleanup={handleManualCleanup}
                    isCleaningUp={isCleaningUp}
                    cleanupMessage={cleanupMessage}
                />
            </div>
        </div>
    );
};

export default SmartStorageManager;