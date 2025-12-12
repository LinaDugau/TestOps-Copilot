import { useState, ChangeEvent, MouseEvent } from 'react';
import axios from 'axios';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import {
  Button,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Box,
  Typography,
  TextField,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Tooltip,
  IconButton,
  AppBar,
  Toolbar,
  Switch,
  FormControlLabel,
  Menu,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Divider,
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import InfoIcon from '@mui/icons-material/Info';
import AppsIcon from '@mui/icons-material/Apps';
import SettingsIcon from '@mui/icons-material/Settings';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import NotificationsNoneIcon from '@mui/icons-material/NotificationsNone';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import BuildIcon from '@mui/icons-material/Build';
import CloseIcon from '@mui/icons-material/Close';
import EditIcon from '@mui/icons-material/Edit';

type CustomPrompt = { name: string; prompt: string };

const apiBaseUrl =
  process.env.REACT_APP_API_URL ||
  (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

const api = axios.create({
  baseURL: apiBaseUrl,
});

function App() {
  const [type, setType] = useState('test_plan');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastGeneratedCode, setLastGeneratedCode] = useState<string>('');
  const [repoId, setRepoId] = useState<string>('');
  const [branch, setBranch] = useState<string>('main');
  const [filePath, setFilePath] = useState<string>('tests/generated_tests.py');
  const [commitMessage, setCommitMessage] = useState<string>('Generated tests from TestOps Copilot');
  const [committing, setCommitting] = useState<boolean>(false);
  const [commitResult, setCommitResult] = useState<string | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitDialogOpen, setCommitDialogOpen] = useState<boolean>(false);
  const [repoIdForDefects, setRepoIdForDefects] = useState<string>('');
  const [defectsLoading, setDefectsLoading] = useState<boolean>(false);
  const [defectsDialogOpen, setDefectsDialogOpen] = useState<boolean>(false);
  const [defectsSummary, setDefectsSummary] = useState<string | null>(null);
  const [defectsError, setDefectsError] = useState<string | null>(null);
  const [defectsLabels, setDefectsLabels] = useState<string>('bug');
  const [defectsState, setDefectsState] = useState<'all' | 'opened' | 'closed'>('all');
  const [darkTheme, setDarkTheme] = useState<boolean>(false);
  const [settingsAnchorEl, setSettingsAnchorEl] = useState<null | HTMLElement>(null);
  const [helpAnchorEl, setHelpAnchorEl] = useState<null | HTMLElement>(null);
  const [customType, setCustomType] = useState<string>('');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [userProvidedCode, setUserProvidedCode] = useState<string>('');
  const [customDialogOpen, setCustomDialogOpen] = useState<boolean>(false);
  const [customPrompts, setCustomPrompts] = useState<CustomPrompt[]>(() => {
    try {
      const saved = localStorage.getItem('custom_prompts');
      const parsed: CustomPrompt[] = saved ? JSON.parse(saved) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      console.error('Failed to load custom_prompts from localStorage', err);
      return [];
    }
  });
  const [manageDialogOpen, setManageDialogOpen] = useState<boolean>(false);
  const [editingPrompt, setEditingPrompt] = useState<{ name: string; prompt: string; type: string; isCustom: boolean; originalName?: string } | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState<boolean>(false);
  const [editedBuiltinPrompts, setEditedBuiltinPrompts] = useState<{ type: string; name: string; prompt: string }[]>(() => {
    try {
      const saved = localStorage.getItem('edited_builtin_prompts');
      const parsed = saved ? JSON.parse(saved) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      console.error('Failed to load edited_builtin_prompts from localStorage', err);
      return [];
    }
  });

  const saveCustomPrompts = (prompts: CustomPrompt[]) => {
    localStorage.setItem('custom_prompts', JSON.stringify(prompts));
    setCustomPrompts(prompts);
  };

  const saveEditedBuiltin = (prompts: { type: string; name: string; prompt: string }[]) => {
    localStorage.setItem('edited_builtin_prompts', JSON.stringify(prompts));
    setEditedBuiltinPrompts(prompts);
  };

  const handleCustomCreate = () => {
    const name = customType.trim();
    const promptValue = customPrompt.trim();

    if (!name || !promptValue) {
      return;
    }

    if (promptValue.length > 5000) {
      setError('Промпт превышает 5000 символов (лимит 5000)');
      return;
    }

    const filtered = customPrompts.filter((p: CustomPrompt) => p.name !== name);
    const updated = [...filtered, { name, prompt: promptValue }];
    saveCustomPrompts(updated);
    setCustomDialogOpen(false);
    setType('custom');
  };

  const handleCustomSelect = (promptName: string) => {
    const found = customPrompts.find((p: CustomPrompt) => p.name === promptName);
    if (found) {
      setCustomType(found.name);
      setCustomPrompt(found.prompt);
    }
  };

  const handleCustomUse = (promptName: string) => {
    const found = customPrompts.find((p: CustomPrompt) => p.name === promptName);
    if (found) {
      setCustomType(found.name);
      setCustomPrompt(found.prompt);
      setType('custom');
      setCustomDialogOpen(false);
    }
  };

  const handleCustomDelete = (promptName: string) => {
    const filtered = customPrompts.filter((p: CustomPrompt) => p.name !== promptName);
    saveCustomPrompts(filtered);
    if (customType === promptName) {
      setCustomType('');
      setCustomPrompt('');
    }
  };

  const loadOriginalPrompt = async (promptType: string) => {
    try {
      const res = await api.get(`/prompt/${promptType}`);
      return res.data?.prompt || '';
    } catch (e) {
      console.error('Ошибка загрузки оригинала:', e);
      return '';
    }
  };

  const openEdit = async (item: { name: string; prompt: string; type?: string; isCustom?: boolean }) => {
    const basePayload = {
      ...item,
      isCustom: !!item.isCustom,
      type: item.type || '',
      originalName: item.name,
    };

    setEditingPrompt(basePayload);
    setEditDialogOpen(true);

    if (item.type && !item.isCustom) {
      const edited = editedBuiltinPrompts.find((p) => p.type === item.type);
      if (edited) {
        setEditingPrompt((prev) => (prev ? { ...prev, prompt: edited.prompt } : prev));
        return;
      }
      const original = await loadOriginalPrompt(item.type);
      setEditingPrompt((prev) => (prev ? { ...prev, prompt: original } : prev));
    }
  };

  const handleSaveEdit = () => {
    if (!editingPrompt) return;

    const trimmedPrompt = editingPrompt.prompt.trim();
    const trimmedName = editingPrompt.name.trim();

    if (!trimmedPrompt || !trimmedName) {
      return;
    }

    if (trimmedPrompt.length > 8000) {
      setError('Промпт превышает 8000 символов (лимит 8000)');
      return;
    }

    if (editingPrompt.isCustom) {
      const targetName = editingPrompt.originalName || editingPrompt.name;
      const filtered = customPrompts.filter((p) => p.name !== targetName);
      const updatedCustom = [...filtered, { name: trimmedName, prompt: trimmedPrompt }];
      saveCustomPrompts(updatedCustom);

      if (customType === targetName) {
        setCustomType(trimmedName);
        setCustomPrompt(trimmedPrompt);
        setType('custom');
      }
    } else {
      const updatedEdited = editedBuiltinPrompts.filter((p) => p.type !== editingPrompt.type);
      if (trimmedPrompt) {
        updatedEdited.push({ type: editingPrompt.type, name: trimmedName || editingPrompt.name, prompt: trimmedPrompt });
      }
      saveEditedBuiltin(updatedEdited);
    }

    setEditDialogOpen(false);
    setEditingPrompt(null);
  };

  const handleResetToDefault = async () => {
    if (!editingPrompt || editingPrompt.isCustom) return;

    const original = await loadOriginalPrompt(editingPrompt.type);
    setEditingPrompt((prev) => (prev ? { ...prev, prompt: original } : prev));

    const updated = editedBuiltinPrompts.filter((p) => p.type !== editingPrompt.type);
    saveEditedBuiltin(updated);
  };

  const generate = async () => {
    setResult(null);
    setError(null);

    if (type === 'custom') {
      const trimmed = customPrompt.trim();
      if (!trimmed) {
        setError('Введите промпт для кастомного сценария');
        return;
      }
      if (trimmed.length > 8000) {
        setError('Промпт превышает 8000 символов (лимит 8000)');
        return;
      }
    } else if (type === 'optimize' || type === 'test_plan') {
      if (userProvidedCode.length > 10000) {
        setError('Код для анализа превышает 10000 символов');
        return;
      }
      if (!userProvidedCode.trim() && !lastGeneratedCode) {
        setError('Для этого режима добавьте код вручную или сгенерируйте его ранее');
        return;
      }
    } else {
      const edited = editedBuiltinPrompts.find((p) => p.type === type);
      if (edited) {
        const trimmed = edited.prompt.trim();
        if (!trimmed) {
          setError('Отредактированный промпт пуст — обновите текст или сбросьте по умолчанию');
          return;
        }
        if (trimmed.length > 8000) {
          setError('Промпт превышает 8000 символов (лимит 8000)');
          return;
        }
      }
    }

    setLoading(true);

    try {
      const payload: any = { type };
      const edited = editedBuiltinPrompts.find((p) => p.type === type);

      if (type === 'custom') {
        payload.custom_prompt = customPrompt.trim();
      } else if (edited) {
        payload.custom_prompt = edited.prompt.trim();
      }

      if (type === 'test_plan' || type === 'optimize' || type === 'unit_ci') {
        if (userProvidedCode.trim()) {
          payload.previous_code = userProvidedCode.trim();
        } else if (lastGeneratedCode) {
          payload.previous_code = lastGeneratedCode;
        }
      }

      if (type === 'optimize' && repoIdForDefects) {
        const repoIdValue = /^\d+$/.test(repoIdForDefects.trim()) ? parseInt(repoIdForDefects.trim()) : repoIdForDefects.trim();
        payload.repo_id = repoIdValue;
      }

      const res = await api.post('/generate', payload);
      const generatedCode = res.data.code || '';

      setResult(res.data);
      if (type.includes('manual') || type.includes('auto') || type === 'unit_ci' || type === 'custom') {
        setLastGeneratedCode(generatedCode);
      }
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || 'Неизвестная ошибка';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const commit = async () => {
    if (!result || !result.code) {
      setCommitError('Нет сгенерированного кода для коммита');
      return;
    }

    if (!repoId || !filePath) {
      setCommitError('Заполните все обязательные поля (ID репозитория и путь к файлу)');
      return;
    }

    setCommitting(true);
    setCommitError(null);
    setCommitResult(null);

    try {
      const repoIdValue = /^\d+$/.test(repoId.trim()) ? parseInt(repoId.trim()) : repoId.trim();
      
      const res = await api.post('/commit', {
        repo_id: repoIdValue,
        branch: branch || 'main',
        file_path: filePath,
        commit_message: commitMessage || 'Generated tests from TestOps Copilot',
        code: result.code
      });

      setCommitResult(`Успешно! Коммит: ${res.data.commit_sha || 'создан'}`);
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || 'Неизвестная ошибка';
      setCommitError(msg);
    } finally {
      setCommitting(false);
    }
  };

  const analyzeDefects = async () => {
    if (!repoIdForDefects.trim()) {
      setDefectsError('Укажите Repo ID для анализа багов');
      return;
    }

    setDefectsLoading(true);
    setDefectsError(null);
    setDefectsSummary(null);

    const repoIdValue = /^\d+$/.test(repoIdForDefects.trim()) ? parseInt(repoIdForDefects.trim()) : repoIdForDefects.trim();
    const labels = defectsLabels
      .split(',')
      .map((l: string) => l.trim())
      .filter(Boolean);

    try {
      const res = await api.post('/analyze_defects', {
        repo_id: repoIdValue,
        labels: labels.length ? labels : ['bug'],
        state: defectsState,
      });
      setDefectsSummary(res.data.summary || 'Нет данных по багам');
      setDefectsDialogOpen(false);
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || 'Не удалось загрузить баги';
      setDefectsError(msg);
    } finally {
      setDefectsLoading(false);
    }
  };

  const options = [
    { value: 'manual_ui', label: 'Ручные тесты — UI Калькулятор (28+ кейсов)' },
    { value: 'manual_api', label: 'Ручные тесты — API Evolution Compute (29+ кейсов)' },
    { value: 'auto_ui', label: 'Автоматические e2e UI тесты (Playwright + pytest)' },
    { value: 'auto_api', label: 'Автоматические API тесты (pytest + requests + allure)' },
    { value: 'test_plan', label: 'Генератор тест-плана (MVP v1.1)' },
    { value: 'optimize', label: 'Оптимизация тестов (дубли, покрытие, полный код)' },
    { value: 'unit_ci', label: 'Unit-тесты для CI/CD (pytest + .gitlab-ci.yml)' },
  ];

  const selectValue = type === 'custom' && customType ? `custom::${customType}` : type;

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: darkTheme ? '#1a1a1a' : '#f5f5f5', position: 'relative' }}>
      {/* Top Header Bar */}
      <AppBar position="static" elevation={0} sx={{ bgcolor: darkTheme ? '#2d2d2d' : 'white', color: darkTheme ? 'white' : '#333', borderBottom: darkTheme ? '1px solid #444' : '1px solid #e0e0e0' }}>
        <Toolbar sx={{ minHeight: '48px !important', px: 2 }}>
          <AppsIcon sx={{ mr: 1, color: darkTheme ? '#ccc' : '#666', fontSize: 20 }} />
          <Box
            component="img"
            src="/logo-h.svg"
            alt="Logo"
            sx={{
              width: 20,
              height: 20,
              mr: 1.5,
              objectFit: 'contain',
            }}
          />
          <Typography variant="body2" sx={{ flexGrow: 1, color: darkTheme ? '#ccc' : '#666', fontSize: '14px' }}>
            cloud.ru / TestOps Copilot
          </Typography>
          <IconButton 
            size="small" 
            sx={{ color: darkTheme ? '#ccc' : '#666', mr: 0.5 }}
            onClick={(e: MouseEvent<HTMLElement>) => setSettingsAnchorEl(e.currentTarget)}
          >
            <SettingsIcon fontSize="small" />
          </IconButton>
          <IconButton 
            size="small" 
            sx={{ color: darkTheme ? '#ccc' : '#666', mr: 0.5 }}
            onClick={(e: MouseEvent<HTMLElement>) => setHelpAnchorEl(e.currentTarget)}
          >
            <HelpOutlineIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" sx={{ color: darkTheme ? '#ccc' : '#666', mr: 0.5 }}>
            <NotificationsNoneIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" sx={{ color: darkTheme ? '#ccc' : '#666' }}>
            <AccountCircleIcon fontSize="small" />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          pt: 8,
          px: 2,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: 4,
            bgcolor: darkTheme ? '#2d2d2d' : 'white',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '1140px',
            border: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
            color: darkTheme ? 'white' : 'inherit',
          }}
        >
          <Box 
            sx={{ 
              mb: 3,
              top: 0,
              zIndex: 100,
              bgcolor: darkTheme ? '#2d2d2d' : 'white',
              pt: 2,
              pb: 2,
              mt: -2,
              mx: -2,
              px: 2,
            }}
          >
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Select
                value={selectValue}
                onChange={(e: SelectChangeEvent) => {
                  const newValue = e.target.value;
                  if (newValue === 'custom_create') {
                    setCustomDialogOpen(true);
                    setType('custom');
                    setCustomType('');
                    setCustomPrompt('');
                    return;
                  }

                  if (typeof newValue === 'string' && newValue.startsWith('custom::')) {
                    const name = newValue.replace('custom::', '');
                    const found = customPrompts.find((p: CustomPrompt) => p.name === name);
                    setType('custom');
                    if (found) {
                      setCustomType(found.name);
                      setCustomPrompt(found.prompt);
                    } else {
                      setCustomType(name);
                    }
                    return;
                  }

                  setType(newValue as string);
                }}
                fullWidth
                sx={{
                  bgcolor: darkTheme ? '#3d3d3d' : 'white',
                  color: darkTheme ? 'white' : '#333',
                  border: darkTheme ? '1px solid #555' : '1px solid #e0e0e0',
                  borderRadius: '4px',
                  '& .MuiOutlinedInput-notchedOutline': {
                    border: 'none',
                  },
                  '& .MuiSvgIcon-root': {
                    color: darkTheme ? 'white' : '#333',
                  },
                }}
              >
                {options.map((o) => (
                  <MenuItem key={o.value} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
                <MenuItem disabled divider value="__custom_header">
                  — Кастомные —
                </MenuItem>
                {customPrompts.map((cp: CustomPrompt) => (
                  <MenuItem key={`custom-${cp.name}`} value={`custom::${cp.name}`}>
                    ★: {cp.name}
                  </MenuItem>
                ))}
                <MenuItem value="custom_create">Создать свой сценарий для тестирования</MenuItem>
              </Select>
              <IconButton
                onClick={() => setManageDialogOpen(true)}
                sx={{ color: darkTheme ? '#ccc' : '#666' }}
                title="Управление сценариями"
              >
                <EditIcon fontSize="small" />
              </IconButton>
            </Box>
          </Box>

          <Dialog 
            open={manageDialogOpen} 
            onClose={() => setManageDialogOpen(false)} 
            maxWidth="sm" 
            fullWidth
            PaperProps={{
              sx: {
                bgcolor: darkTheme ? '#2d2d2d' : 'white',
                color: darkTheme ? 'white' : 'inherit',
                borderRadius: '8px',
              }
            }}
          >
            <DialogTitle 
              sx={{ 
                color: '#26D07C',
                fontWeight: 'bold',
                borderBottom: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
                pb: 2,
              }}
            >
              Управление сценариями
            </DialogTitle>
            <DialogContent sx={{ bgcolor: darkTheme ? '#2d2d2d' : 'inherit', color: darkTheme ? 'white' : 'inherit' }}>
              <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: darkTheme ? 'white' : 'inherit' }}>Встроенные сценарии</Typography>
              <List dense>
                {options.map((o) => {
                  const edited = editedBuiltinPrompts.find((p) => p.type === o.value);
                  return (
                    <ListItem key={o.value} disablePadding>
                      <ListItemButton 
                        onClick={() => openEdit({ name: o.label, prompt: edited?.prompt || '', type: o.value, isCustom: false })}
                        sx={{
                          '&:hover': {
                            bgcolor: darkTheme ? '#3d3d3d' : 'rgba(0, 0, 0, 0.04)',
                          },
                        }}
                      >
                        <ListItemText
                          primary={o.label}
                          secondary={edited ? 'Отредактировано' : 'Оригинал'}
                          primaryTypographyProps={{ color: darkTheme ? 'white' : 'inherit' }}
                          secondaryTypographyProps={{ color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)' }}
                        />
                      </ListItemButton>
                    </ListItem>
                  );
                })}
              </List>
              <Divider sx={{ my: 2, borderColor: darkTheme ? '#444' : '#e0e0e0' }} />
              <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: darkTheme ? 'white' : 'inherit' }}>Ваши сценарии</Typography>
              <List dense>
                {customPrompts.map((p) => (
                  <ListItem key={p.name} disablePadding>
                    <ListItemButton 
                      onClick={() => openEdit({ name: p.name, prompt: p.prompt, type: '', isCustom: true })}
                      sx={{
                        '&:hover': {
                          bgcolor: darkTheme ? '#3d3d3d' : 'rgba(0, 0, 0, 0.04)',
                        },
                      }}
                    >
                      <ListItemText 
                        primary={p.name}
                        primaryTypographyProps={{ color: darkTheme ? 'white' : 'inherit' }}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
                {customPrompts.length === 0 && (
                  <ListItem>
                    <ListItemText 
                      primary="Нет пользовательских сценариев"
                      primaryTypographyProps={{ color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)' }}
                    />
                  </ListItem>
                )}
              </List>
            </DialogContent>
            <DialogActions 
              sx={{ 
                p: 2,
                borderTop: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
                bgcolor: darkTheme ? '#2d2d2d' : 'inherit',
              }}
            >
              <Button 
                onClick={() => setManageDialogOpen(false)}
                sx={{
                  color: darkTheme ? '#ccc' : '#666',
                  '&:hover': {
                    bgcolor: darkTheme ? '#3d3d3d' : 'rgba(0, 0, 0, 0.04)',
                  },
                }}
              >
                Закрыть
              </Button>
              <Button
                onClick={() => {
                  setManageDialogOpen(false);
                  setCustomType('');
                  setCustomPrompt('');
                  setCustomDialogOpen(true);
                }}
                variant="contained"
                sx={{
                  bgcolor: '#26D07C',
                  color: '#000000',
                  fontWeight: 'bold',
                  '&:hover': {
                    bgcolor: '#20b86d',
                  },
                }}
              >
                Добавить новый
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog 
            open={editDialogOpen} 
            onClose={() => setEditDialogOpen(false)} 
            maxWidth="md" 
            fullWidth
            PaperProps={{
              sx: {
                bgcolor: darkTheme ? '#2d2d2d' : 'white',
                color: darkTheme ? 'white' : 'inherit',
                borderRadius: '8px',
              }
            }}
          >
            <DialogTitle 
              sx={{ 
                color: '#26D07C',
                fontWeight: 'bold',
                borderBottom: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
                pb: 2,
              }}
            >
              Редактирование сценария: {editingPrompt?.name}
            </DialogTitle>
            <DialogContent sx={{ bgcolor: darkTheme ? '#2d2d2d' : 'inherit', color: darkTheme ? 'white' : 'inherit' }}>
              <TextField
                label="Название"
                value={editingPrompt?.name || ''}
                onChange={(e) => setEditingPrompt((prev) => (prev ? { ...prev, name: e.target.value } : prev))}
                fullWidth
                margin="normal"
                disabled={!editingPrompt?.isCustom}
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: darkTheme ? '#3d3d3d' : 'white',
                    color: darkTheme ? 'white' : 'inherit',
                    '&.Mui-disabled': {
                      color: darkTheme ? 'white !important' : 'inherit',
                      '-webkit-text-fill-color': darkTheme ? 'white !important' : 'inherit',
                    },
                  },
                  '& .MuiInputBase-input': {
                    color: darkTheme ? 'white !important' : 'inherit',
                    '&.Mui-disabled': {
                      color: darkTheme ? 'white !important' : 'inherit',
                      '-webkit-text-fill-color': darkTheme ? 'white !important' : 'inherit',
                    },
                  },
                  '& input': {
                    color: darkTheme ? 'white !important' : 'inherit',
                    '&:disabled': {
                      color: darkTheme ? 'white !important' : 'inherit',
                      '-webkit-text-fill-color': darkTheme ? 'white !important' : 'inherit',
                    },
                  },
                  '& .MuiInputLabel-root': {
                    color: darkTheme ? '#ccc' : 'inherit',
                  },
                  '& .MuiFormHelperText-root': {
                    color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)',
                  },
                }}
              />
              <TextField
                label="Промпт"
                value={editingPrompt?.prompt || ''}
                onChange={(e) => setEditingPrompt((prev) => (prev ? { ...prev, prompt: e.target.value } : prev))}
                fullWidth
                margin="normal"
                multiline
                rows={10}
                inputProps={{ maxLength: 8000 }}
                helperText={`Длина: ${editingPrompt?.prompt?.length || 0}/8000`}
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: darkTheme ? '#3d3d3d' : 'white',
                    color: darkTheme ? 'white' : 'inherit',
                  },
                  '& .MuiInputLabel-root': {
                    color: darkTheme ? '#ccc' : 'inherit',
                  },
                  '& .MuiFormHelperText-root': {
                    color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)',
                  },
                }}
              />
            </DialogContent>
            <DialogActions 
              sx={{ 
                p: 2,
                borderTop: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
                bgcolor: darkTheme ? '#2d2d2d' : 'inherit',
              }}
            >
              {!editingPrompt?.isCustom && (
                <Button
                  variant="outlined"
                  onClick={handleResetToDefault}
                  sx={{ 
                    mr: 'auto',
                    ml: 1,
                    borderColor: '#26D07C',
                    color: '#26D07C',
                    '&:hover': {
                      borderColor: '#20b86d',
                      bgcolor: darkTheme ? 'rgba(38, 208, 124, 0.1)' : 'rgba(38, 208, 124, 0.05)',
                    },
                    '&:disabled': {
                      borderColor: darkTheme ? '#555' : '#e0e0e0',
                      color: darkTheme ? '#666' : '#999',
                    },
                  }}
                  disabled={!editingPrompt}
                >
                  По умолчанию
                </Button>
              )}
              <Button
                onClick={() => {
                  setEditDialogOpen(false);
                  setEditingPrompt(null);
                }}
                sx={{
                  color: darkTheme ? '#ccc' : '#666',
                  '&:hover': {
                    bgcolor: darkTheme ? '#3d3d3d' : 'rgba(0, 0, 0, 0.04)',
                  },
                }}
              >
                Отмена
              </Button>
              <Button 
                onClick={handleSaveEdit} 
                variant="contained" 
                disabled={!editingPrompt?.prompt?.trim()}
                sx={{
                  bgcolor: '#26D07C',
                  color: '#000000',
                  fontWeight: 'bold',
                  '&:hover': {
                    bgcolor: '#20b86d',
                  },
                  '&:disabled': {
                    bgcolor: darkTheme ? '#3d3d3d' : '#e0e0e0',
                    color: darkTheme ? '#666' : '#999',
                  },
                }}
              >
                Сохранить
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog 
            open={customDialogOpen} 
            onClose={() => setCustomDialogOpen(false)} 
            maxWidth="md" 
            fullWidth
            PaperProps={{
              sx: {
                bgcolor: darkTheme ? '#2d2d2d' : 'white',
                color: darkTheme ? 'white' : 'inherit',
                borderRadius: '8px',
              }
            }}
          >
            <DialogTitle 
              sx={{ 
                color: '#26D07C',
                fontWeight: 'bold',
                borderBottom: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
                pb: 2,
              }}
            >
              Создать свой сценарий для тестирования
            </DialogTitle>
            <DialogContent sx={{ bgcolor: darkTheme ? '#2d2d2d' : 'inherit', color: darkTheme ? 'white' : 'inherit' }}>
              <TextField
                label="Название сценария"
                value={customType}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setCustomType(e.target.value)}
                fullWidth
                margin="normal"
                placeholder="Например: 'Custom API Tests'"
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: darkTheme ? '#3d3d3d' : 'white',
                    color: darkTheme ? 'white' : 'inherit',
                  },
                  '& .MuiInputLabel-root': {
                    color: darkTheme ? '#ccc' : 'inherit',
                  },
                  '& .MuiFormHelperText-root': {
                    color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)',
                  },
                }}
              />
              <TextField
                label="Промпт (инструкция для модели)"
                value={customPrompt}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setCustomPrompt(e.target.value)}
                fullWidth
                margin="normal"
                multiline
                rows={10}
                placeholder="Опишите, что должна сгенерировать модель (например: 'Сгенерируй тесты для endpoint /users...'). Макс. 5000 символов."
                helperText={`Текущая длина: ${customPrompt.length}/5000. Модель всегда останется в роли QA-помощника.`}
                inputProps={{ maxLength: 5000 }}
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: darkTheme ? '#3d3d3d' : 'white',
                    color: darkTheme ? 'white' : 'inherit',
                  },
                  '& .MuiInputLabel-root': {
                    color: darkTheme ? '#ccc' : 'inherit',
                  },
                  '& .MuiFormHelperText-root': {
                    color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)',
                  },
                }}
              />
              <Typography variant="body2" sx={{ mt: 1, color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)' }}>
                Примечание: Модель будет использовать этот промпт, но с префиксом для фокуса на QA-задачах.
              </Typography>

              {customPrompts.length > 0 && (
                <Box sx={{ mt: 2, borderTop: darkTheme ? '1px solid #444' : '1px solid #e0e0e0', pt: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1, color: darkTheme ? 'white' : 'inherit' }}>
                    Сохраненные сценарии
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {customPrompts.map((cp: CustomPrompt) => (
                      <Box
                        key={cp.name}
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: 1,
                          border: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
                          borderRadius: '6px',
                          p: 1,
                          bgcolor: darkTheme ? '#3d3d3d' : 'transparent',
                        }}
                      >
                        <Box sx={{ minWidth: 0 }}>
                          <Typography variant="body2" sx={{ fontWeight: 600, color: darkTheme ? 'white' : 'inherit' }}>
                            {cp.name}
                          </Typography>
                          <Typography variant="caption" noWrap sx={{ display: 'block', maxWidth: '440px', color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)' }}>
                            {cp.prompt}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
                          <Button 
                            size="small" 
                            onClick={() => handleCustomSelect(cp.name)}
                            sx={{ color: darkTheme ? '#ccc' : 'inherit' }}
                          >
                            Заполнить
                          </Button>
                          <Button 
                            size="small" 
                            variant="outlined" 
                            onClick={() => handleCustomUse(cp.name)}
                            sx={{ 
                              borderColor: darkTheme ? '#555' : '#e0e0e0',
                              color: darkTheme ? '#ccc' : 'inherit',
                            }}
                          >
                            Использовать
                          </Button>
                          <IconButton size="small" color="error" onClick={() => handleCustomDelete(cp.name)}>
                            <CloseIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
            </DialogContent>
            <DialogActions 
              sx={{ 
                p: 2,
                borderTop: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
                justifyContent: 'center',
                bgcolor: darkTheme ? '#2d2d2d' : 'inherit',
              }}
            >
              <Button 
                onClick={() => setCustomDialogOpen(false)}
                sx={{
                  color: darkTheme ? '#ccc' : '#666',
                  '&:hover': {
                    bgcolor: darkTheme ? '#3d3d3d' : 'rgba(0, 0, 0, 0.04)',
                  },
                }}
              >
                Отмена
              </Button>
              <Button 
                onClick={handleCustomCreate} 
                variant="contained" 
                disabled={!customType.trim() || !customPrompt.trim()}
                sx={{ 
                  bgcolor: '#26D07C', 
                  color: '#000000', 
                  fontWeight: 'bold',
                  fontSize: '16px',
                  textTransform: 'uppercase',
                  '&:hover': { 
                    bgcolor: '#20b86d' 
                  },
                  '&:disabled': {
                    bgcolor: darkTheme ? '#3d3d3d' : '#e0e0e0',
                    color: darkTheme ? '#666' : '#999',
                  },
                  py: 1.5,
                  px: 4,
                }}
              >
                Сохранить и использовать
              </Button>
            </DialogActions>
          </Dialog>

          <Box 
            sx={{ 
              display: 'flex', 
              justifyContent: 'flex-start', 
              alignItems: 'center', 
              gap: 2, 
              flexWrap: 'wrap',
              top: 80,
              zIndex: 100,
              bgcolor: darkTheme ? '#2d2d2d' : 'white',
              pt: 2,
              pb: 2,
              mt: -2,
              mx: -2,
              px: 2,
            }}
          >
            {(type === 'optimize' || type === 'test_plan') && (
              <Box sx={{ width: '100%' }}>
                <TextField
                  label="Ваш готовый код для анализа (опционально)"
                  value={userProvidedCode}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setUserProvidedCode(e.target.value)}
                  fullWidth
                  multiline
                  rows={6}
                  placeholder="Вставьте сюда существующий код. Если оставить пустым — будет использован последний сгенерированный."
                  helperText={`Длина: ${userProvidedCode.length}/10000 символов. Приоритет: ваш код > последний сгенерированный.`}
                  inputProps={{ maxLength: 10000 }}
                  sx={{ 
                    '& .MuiInputBase-root': { bgcolor: darkTheme ? '#3d3d3d' : 'white' },
                    '& .MuiInputLabel-root': { color: darkTheme ? '#ccc' : '#333333' },
                    '& .MuiFormHelperText-root': { color: darkTheme ? '#ccc' : 'rgba(0, 0, 0, 0.6)' }
                  }}
                />
                {userProvidedCode && (
                  <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-end' }}>
                    <Button size="small" onClick={() => setUserProvidedCode('')}>
                      Очистить
                    </Button>
                  </Box>
                )}
              </Box>
            )}

            <Button
              variant="contained"
              size="large"
              onClick={generate}
              disabled={loading}
              sx={{
                bgcolor: '#26D07C',
                color: '#000000',
                fontWeight: 'bold',
                fontSize: '16px',
                textTransform: 'uppercase',
                '&:hover': { bgcolor: '#20b86d' },
                py: 1.5,
                px: 4,
                borderRadius: '4px',
              }}
            >
              {loading ? <CircularProgress size={24} sx={{ color: '#000000' }} /> : 'СГЕНЕРИРОВАТЬ'}
            </Button>
            {result && result.metrics && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" sx={{ color: '#666', fontSize: '0.9rem' }}>
                  Время: {result.metrics?.duration_s ?? '—'} с | Память: {result.metrics?.memory_mb ?? '—'} МБ
                  {result.metrics?.per_case_s ? ` | На кейс: ${result.metrics.per_case_s} с` : ''}
                </Typography>
                {(type === 'test_plan' || type === 'optimize') && lastGeneratedCode && (
                  <Tooltip 
                    title="По умолчанию используется последний сгенерированный код для анализа"
                    componentsProps={{
                      tooltip: {
                        sx: { fontSize: '18px', padding: '14px' }
                      }
                    }}
                  >
                    <InfoIcon sx={{ color: '#26D07C', fontSize: 24, flexShrink: 0 }} />
                  </Tooltip>
                )}
              </Box>
            )}
          </Box>

          {error && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-start' }}>
              <Alert
                severity="error"
                sx={{
                  fontSize: '0.9rem',
                  bgcolor: 'transparent',
                  whiteSpace: 'pre-wrap',
                  p: 0,
                }}
              >
                {error}
              </Alert>
            </Box>
          )}

          {result && result.validation && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-start' }}>
              <Alert
                severity={result.validation.valid ? 'success' : 'warning'}
                sx={{
                  fontSize: '0.95rem',
                  bgcolor: 'transparent',
                  '& .MuiAlert-icon': {
                    color: result.validation.valid ? '#26D07C' : undefined,
                  },
                  '& .MuiAlert-message': {
                    color: result.validation.valid ? '#26D07C' : undefined,
                  },
                }}
              >
                {result.validation.valid
                  ? 'Валидация пройдена! 100% соответствует стандартам Allure'
                  : `Найдены проблемы: ${result.validation.issues.join(', ')}`}
              </Alert>
            </Box>
          )}

          {result && type === 'optimize' && (
            <Paper 
              elevation={0} 
              sx={{ 
                mt: 3, 
                p: 3, 
                bgcolor: darkTheme ? '#3d3d3d' : 'white', 
                borderRadius: 2,
                border: '2px solid #26D07C',
                color: darkTheme ? 'white' : 'inherit'
              }}
            >
              <Typography variant="h6" gutterBottom color="#26D07C">
                Анализ исторических дефектов GitLab
              </Typography>
              <Typography variant="body2" sx={{ color: darkTheme ? '#9ca3af' : '#666', mb: 2 }}>
                Получите сводку багов и учтите частые дефекты в рекомендациях и оптимизации.
              </Typography>
              <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
                <Button
                  variant="contained"
                  onClick={() => {
                    setDefectsDialogOpen(true);
                    setDefectsError(null);
                  }}
                  sx={{ bgcolor: '#26D07C', color: '#0b1220', fontWeight: 'bold' }}
                >
                  Анализ дефектов
                </Button>
                {defectsLoading && <CircularProgress size={22} sx={{ color: '#26D07C' }} />}
              </Box>
              {defectsError && (
                <Alert severity="error" sx={{ mt: 2, whiteSpace: 'pre-wrap', bgcolor: darkTheme ? '#2d2d2d' : 'transparent', color: darkTheme ? 'white' : 'inherit' }}>
                  {defectsError}
                </Alert>
              )}
              {defectsSummary && (
                <Alert severity="info" sx={{ mt: 2, whiteSpace: 'pre-wrap', bgcolor: darkTheme ? '#2d2d2d' : 'transparent', color: darkTheme ? 'white' : 'inherit' }}>
                  {defectsSummary}
                </Alert>
              )}
            </Paper>
          )}
        </Paper>
      </Box>

      {/* Commit Button - Bottom Right */}
      {result && result.code && (
        <Button
          variant="contained"
          onClick={() => {
            setCommitDialogOpen(true);
            setCommitError(null);
            setCommitResult(null);
          }}
          disabled={committing}
          sx={{
            position: 'fixed',
            bottom: 0,
            right: '70px',
            bgcolor: '#26D07C',
            color: '#000000',
            fontWeight: 600,
            fontSize: '15px',
            textTransform: 'uppercase',
            '&:hover': { bgcolor: '#20b86d' },
            py: 1,
            px: 6,
            borderRadius: '10px 20px 0 0',
            boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            zIndex: 1000,
          }}
        >
          Коммит в GitLab
        </Button>
      )}

      {/* Results Section */}
      {result && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, px: 2, ml: 7, pb: 10 }}>
          <Box sx={{ maxWidth: '1260px', width: '100%', display: 'flex', gap: 2, alignItems: 'flex-start' }}>
            <Paper elevation={2} sx={{ flex: 1, p: 3, bgcolor: darkTheme ? '#2d2d2d' : 'white', borderRadius: '8px', border: darkTheme ? '1px solid #444' : '1px solid #e0e0e0', minWidth: 0, color: darkTheme ? 'white' : 'inherit' }}>
              <Typography variant="h6" gutterBottom sx={{ color: '#26D07C', mb: 2 }}>
                {type === 'test_plan' ? 'Тест-план' : type === 'optimize' ? 'Результат оптимизации' : 'Сгенерированный код'}
              </Typography>

              <Box sx={{ minWidth: 0, overflow: 'hidden' }}>
                <SyntaxHighlighter
                  language={type.includes('test_plan') || type === 'optimize' ? 'markdown' : 'python'}
                  style={atomOneDark}
                  showLineNumbers
                  customStyle={{ 
                    borderRadius: '8px', 
                    padding: '20px', 
                    fontSize: '14px',
                    overflow: 'auto',
                    maxWidth: '100%',
                  }}
                >
                  {result.code || '# Ничего не сгенерировано'}
                </SyntaxHighlighter>
              </Box>
            </Paper>

            <Box 
              sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                gap: 1, 
                pt: 2,
                top: 20,
                alignSelf: 'flex-start',
                zIndex: 100,
              }}
            >
              <Tooltip title="Скопировать в буфер">
                <IconButton
                  onClick={() => navigator.clipboard.writeText(result.code || '')}
                  sx={{
                    color: '#666',
                    '&:hover': { color: '#26D07C', bgcolor: 'rgba(38, 208, 124, 0.05)' },
                  }}
                >
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
              {(type.includes('manual') || type.includes('auto')) && (
                <Tooltip title="Оптимизировать эти тесты">
                  <IconButton
                    onClick={() => {
                      setType('optimize');
                      setLastGeneratedCode(result.code);
                    }}
                    sx={{
                      color: '#666',
                      '&:hover': { color: '#26D07C', bgcolor: 'rgba(38, 208, 124, 0.05)' },
                    }}
                  >
                    <BuildIcon />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>
        </Box>
      )}

      {/* Commit Dialog */}
      <Dialog
        open={commitDialogOpen}
        onClose={() => {
          if (!committing) {
            setCommitDialogOpen(false);
            setCommitError(null);
            setCommitResult(null);
          }
        }}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: darkTheme ? '#2d2d2d' : 'white',
            color: darkTheme ? 'white' : 'inherit',
          }
        }}
      >
        <DialogTitle sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          bgcolor: darkTheme ? '#2d2d2d' : 'inherit',
          color: '#26D07C',
          borderBottom: darkTheme ? '1px solid #444' : 'none',
        }}>
          Коммит в GitLab
          <IconButton
            onClick={() => {
              if (!committing) {
                setCommitDialogOpen(false);
                setCommitError(null);
                setCommitResult(null);
              }
            }}
            disabled={committing}
            sx={{ ml: 2, color: darkTheme ? 'white' : 'inherit' }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ bgcolor: darkTheme ? '#2d2d2d' : 'inherit', color: darkTheme ? 'white' : 'inherit' }}>
          <Box display="flex" flexDirection="column" gap={2} mt={1}>
            <TextField
              label="ID репозитория или путь"
              value={repoId}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setRepoId(e.target.value)}
              placeholder="12345 или namespace/project"
              required
              fullWidth
              helperText="Числовой ID: (например 12345) или путь проекта (например: tests/generated_tests.py)"
              sx={{
                '& .MuiInputBase-root': {
                  bgcolor: darkTheme ? '#3d3d3d' : 'white',
                  color: darkTheme ? 'white' : 'inherit',
                },
                '& .MuiInputLabel-root': {
                  color: darkTheme ? '#ccc' : 'inherit',
                },
                '& .MuiFormHelperText-root': {
                  color: darkTheme ? '#aaa' : 'inherit',
                },
              }}
            />
            
            <TextField
              label="Ветка"
              value={branch}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setBranch(e.target.value)}
              placeholder="main"
              fullWidth
              helperText="Название ветки (по умолчанию: main)"
              sx={{
                '& .MuiInputBase-root': {
                  bgcolor: darkTheme ? '#3d3d3d' : 'white',
                  color: darkTheme ? 'white' : 'inherit',
                },
                '& .MuiInputLabel-root': {
                  color: darkTheme ? '#ccc' : 'inherit',
                },
                '& .MuiFormHelperText-root': {
                  color: darkTheme ? '#aaa' : 'inherit',
                },
              }}
            />
            
            <TextField
              label="Путь к файлу"
              value={filePath}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFilePath(e.target.value)}
              placeholder="tests/generated_tests.py"
              required
              fullWidth
              helperText="Путь к файлу в репозитории"
              sx={{
                '& .MuiInputBase-root': {
                  bgcolor: darkTheme ? '#3d3d3d' : 'white',
                  color: darkTheme ? 'white' : 'inherit',
                },
                '& .MuiInputLabel-root': {
                  color: darkTheme ? '#ccc' : 'inherit',
                },
                '& .MuiFormHelperText-root': {
                  color: darkTheme ? '#aaa' : 'inherit',
                },
              }}
            />
            
            <TextField
              label="Сообщение коммита"
              value={commitMessage}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setCommitMessage(e.target.value)}
              placeholder="Generated tests from TestOps Copilot"
              fullWidth
              multiline
              rows={2}
              sx={{
                '& .MuiInputBase-root': {
                  bgcolor: darkTheme ? '#3d3d3d' : 'white',
                  color: darkTheme ? 'white' : 'inherit',
                },
                '& .MuiInputLabel-root': {
                  color: darkTheme ? '#ccc' : 'inherit',
                },
              }}
            />
          </Box>

          {commitError && (
            <Alert severity="error" sx={{ mt: 2, whiteSpace: 'pre-wrap' }}>
              {commitError}
            </Alert>
          )}

          {commitResult && (
            <Alert severity="success" sx={{ mt: 2 }}>
              {commitResult}
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ 
          p: 2, 
          justifyContent: 'center',
          bgcolor: darkTheme ? '#2d2d2d' : 'inherit',
          borderTop: darkTheme ? '1px solid #444' : 'none',
        }}>
          <Button
            variant="contained"
            onClick={async () => {
              await commit();
              if (commitResult && !commitError) {
                setTimeout(() => {
                  setCommitDialogOpen(false);
                }, 2000);
              }
            }}
            disabled={committing || !repoId || !filePath}
            sx={{
              bgcolor: '#26D07C',
              color: '#000000',
              fontWeight: 'bold',
              fontSize: '16px',
              textTransform: 'uppercase',
              '&:hover': { bgcolor: '#20b86d' },
              py: 1.5,
              px: 4,
            }}
          >
            {committing ? <CircularProgress size={20} sx={{ color: '#000000' }} /> : 'КОММИТИТЬ В GITLAB'}
          </Button>
        </DialogActions>
      </Dialog>

      <DefectsDialog
        open={defectsDialogOpen}
        onClose={() => setDefectsDialogOpen(false)}
        repoId={repoIdForDefects}
        setRepoId={setRepoIdForDefects}
        labels={defectsLabels}
        setLabels={setDefectsLabels}
        state={defectsState}
        setState={setDefectsState}
        onSubmit={analyzeDefects}
        loading={defectsLoading}
        darkTheme={darkTheme}
      />

      {/* Settings Menu */}
      <Menu
        anchorEl={settingsAnchorEl}
        open={Boolean(settingsAnchorEl)}
        onClose={() => setSettingsAnchorEl(null)}
        disableScrollLock
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: {
            bgcolor: darkTheme ? '#595959' : 'white',
            color: darkTheme ? 'white' : '#333',
            minWidth: '200px',
            mt: 1,
            ml: -1.25,
            border: darkTheme ? 'none' : '1px solid #e0e0e0',
          }
        }}
      >
        <Box sx={{ p: 2, bgcolor: darkTheme ? '#797979' : '#f5f5f5', borderRadius: '4px', m: 1 }}>
          <FormControlLabel
            control={
              <Switch
                checked={darkTheme}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setDarkTheme(e.target.checked)}
                sx={{
                  '& .MuiSwitch-switchBase.Mui-checked': {
                    color: '#26D07C',
                  },
                  '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                    backgroundColor: '#26D07C',
                  },
                }}
              />
            }
            label="Темная тема"
            sx={{ color: darkTheme ? 'white' : '#333' }}
          />
        </Box>
      </Menu>

      {/* Help Menu */}
      <Menu
        anchorEl={helpAnchorEl}
        open={Boolean(helpAnchorEl)}
        onClose={() => setHelpAnchorEl(null)}
        disableScrollLock
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: {
            bgcolor: darkTheme ? '#595959' : 'white',
            color: darkTheme ? 'white' : '#333',
            minWidth: '200px',
            mt: 1,
            ml: -1.25,
            border: darkTheme ? 'none' : '1px solid #e0e0e0',
          }
        }}
      >
        <Box sx={{ p: 2, bgcolor: darkTheme ? '#797979' : '#f5f5f5', borderRadius: '4px', m: 1 }}>
          <Typography variant="body2" sx={{ color: darkTheme ? 'white' : '#333', textAlign: 'center' }}>
            Разработано командой ХХ 2025
          </Typography>
        </Box>
      </Menu>
    </Box>
  );
}

export default App;

function DefectsDialog(props: {
  open: boolean;
  onClose: () => void;
  repoId: string;
  setRepoId: (v: string) => void;
  labels: string;
  setLabels: (v: string) => void;
  state: 'all' | 'opened' | 'closed';
  setState: (v: 'all' | 'opened' | 'closed') => void;
  onSubmit: () => void;
  loading: boolean;
  darkTheme: boolean;
}) {
  const {
    open,
    onClose,
    repoId,
    setRepoId,
    labels,
    setLabels,
    state,
    setState,
    onSubmit,
    loading,
    darkTheme,
  } = props;

  return (
    <Dialog 
      open={open} 
      onClose={loading ? undefined : onClose} 
      fullWidth 
      maxWidth="md"
      PaperProps={{
        sx: {
          bgcolor: darkTheme ? '#2d2d2d' : 'white',
          color: darkTheme ? 'white' : 'inherit',
          borderRadius: '8px',
          minHeight: '300px',
        }
      }}
    >
      <DialogTitle 
        sx={{ 
          color: '#26D07C',
          fontWeight: 'bold',
          borderBottom: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
          pb: 2,
          
        }}
      >
        Анализ исторических багов GitLab
      </DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2, '&.MuiDialogContent-root': {paddingTop: '10px !important',} }}>
        <TextField
          label="Repo ID или namespace/project"
          value={repoId}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setRepoId(e.target.value)}
          placeholder="123456 или group/project"
          required
          fullWidth
          sx={{
            '& .MuiInputBase-root': {
              bgcolor: darkTheme ? '#3d3d3d' : 'white',
              color: darkTheme ? 'white' : 'inherit',
            },
            '& .MuiInputLabel-root': {
              color: darkTheme ? '#ccc' : 'inherit',
            },
            '& .MuiFormHelperText-root': {
              color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)',
            },
          }}
        />
        <TextField
          label="Метки (через запятую)"
          value={labels}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setLabels(e.target.value)}
          placeholder="bug,defect,Bug"
          helperText="Если пусто — используется 'bug'"
          fullWidth
          sx={{
            '& .MuiInputBase-root': {
              bgcolor: darkTheme ? '#3d3d3d' : 'white',
              color: darkTheme ? 'white' : 'inherit',
            },
            '& .MuiInputLabel-root': {
              color: darkTheme ? '#ccc' : 'inherit',
            },
            '& .MuiFormHelperText-root': {
              color: darkTheme ? '#aaa' : 'rgba(0, 0, 0, 0.6)',
            },
          }}
        />
        <FormControl fullWidth>
          <InputLabel 
            id="defects-state-label"
            sx={{
              color: darkTheme ? '#ccc' : 'inherit',
            }}
          >
            State
          </InputLabel>
          <Select
            labelId="defects-state-label"
            value={state}
            label="State"
            onChange={(e: SelectChangeEvent) => setState(e.target.value as 'all' | 'opened' | 'closed')}
            sx={{
              bgcolor: darkTheme ? '#3d3d3d' : 'white',
              color: darkTheme ? 'white' : 'inherit',
              '& .MuiSvgIcon-root': {
                color: darkTheme ? 'white' : 'inherit',
              },
            }}
            MenuProps={{
              PaperProps: {
                sx: {
                  bgcolor: darkTheme ? '#2d2d2d' : 'white',
                  color: darkTheme ? 'white' : 'inherit',
                  '& .MuiMenuItem-root': {
                    color: darkTheme ? 'white' : 'inherit',
                    '&:hover': {
                      bgcolor: darkTheme ? '#3d3d3d' : 'rgba(0, 0, 0, 0.04)',
                    },
                    '&.Mui-selected': {
                      bgcolor: darkTheme ? '#26D07C' : '#26D07C',
                      color: darkTheme ? '#000000' : '#000000',
                      '&:hover': {
                        bgcolor: darkTheme ? '#20b86d' : '#20b86d',
                      },
                    },
                  },
                },
              },
            }}
          >
            <MenuItem value="all">all</MenuItem>
            <MenuItem value="opened">opened</MenuItem>
            <MenuItem value="closed">closed</MenuItem>
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions 
        sx={{ 
          p: 2,
          borderTop: darkTheme ? '1px solid #444' : '1px solid #e0e0e0',
          justifyContent: 'center',
        }}
      >
        <Button 
          onClick={onClose} 
          disabled={loading} 
          sx={{
            color: darkTheme ? '#ccc' : 'inherit',
            '&:hover': {
              bgcolor: darkTheme ? '#3d3d3d' : 'rgba(0, 0, 0, 0.04)',
            },
          }}
        >
          Отмена
        </Button>
        <Button
          variant="contained"
          onClick={onSubmit}
          disabled={loading || !repoId.trim()}
          sx={{ 
            bgcolor: '#26D07C', 
            color: '#000000', 
            fontWeight: 'bold',
            fontSize: '16px',
            textTransform: 'uppercase',
            '&:hover': { 
              bgcolor: '#20b86d' 
            },
            '&:disabled': {
              bgcolor: darkTheme ? '#3d3d3d' : '#e0e0e0',
              color: darkTheme ? '#666' : '#999',
            },
            py: 1.5,
            px: 4,
          }}
        >
          {loading ? <CircularProgress size={20} sx={{ color: '#000000' }} /> : 'Анализировать'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}