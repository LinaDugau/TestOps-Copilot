import { useState, ChangeEvent } from 'react';
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
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import InfoOutlined from '@mui/icons-material/InfoOutlined';
import InfoIcon from '@mui/icons-material/Info';
import AppsIcon from '@mui/icons-material/Apps';
import SettingsIcon from '@mui/icons-material/Settings';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import NotificationsNoneIcon from '@mui/icons-material/NotificationsNone';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import BuildIcon from '@mui/icons-material/Build';
import CloseIcon from '@mui/icons-material/Close';

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
  const [defectsSummary, setDefectsSummary] = useState<string | null>(null);
  const [defectsError, setDefectsError] = useState<string | null>(null);
  const [defectsLoading, setDefectsLoading] = useState<boolean>(false);
  const [defectsDialogOpen, setDefectsDialogOpen] = useState<boolean>(false);
  const [defectsLabels, setDefectsLabels] = useState<string>('bug');
  const [defectsState, setDefectsState] = useState<'all' | 'opened' | 'closed'>('all');
  const [darkTheme, setDarkTheme] = useState<boolean>(false);
  const [settingsAnchorEl, setSettingsAnchorEl] = useState<null | HTMLElement>(null);
  const [helpAnchorEl, setHelpAnchorEl] = useState<null | HTMLElement>(null);

  const generate = async () => {
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const payload: any = { type };

      if ((type === 'test_plan' || type === 'optimize' || type === 'unit_ci') && lastGeneratedCode) {
        payload.previous_code = lastGeneratedCode;
      }

      if (type === 'optimize' && repoIdForDefects) {
        const repoIdValue = /^\d+$/.test(repoIdForDefects.trim()) ? parseInt(repoIdForDefects.trim()) : repoIdForDefects.trim();
        payload.repo_id = repoIdValue;
      }

      const res = await axios.post('/generate', payload);
      const generatedCode = res.data.code || '';

      setResult(res.data);
      if (type.includes('manual') || type.includes('auto') || type === 'unit_ci') {
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
      
      const res = await axios.post('/commit', {
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
      .map((l) => l.trim())
      .filter(Boolean);

    try {
      const res = await axios.post('/analyze_defects', {
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
            onClick={(e) => setSettingsAnchorEl(e.currentTarget)}
          >
            <SettingsIcon fontSize="small" />
          </IconButton>
          <IconButton 
            size="small" 
            sx={{ color: darkTheme ? '#ccc' : '#666', mr: 0.5 }}
            onClick={(e) => setHelpAnchorEl(e.currentTarget)}
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
              position: 'sticky',
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
            <Select
              value={type}
              onChange={(e: SelectChangeEvent) => setType(e.target.value)}
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
            </Select>
          </Box>

          <Box 
            sx={{ 
              display: 'flex', 
              justifyContent: 'flex-start', 
              alignItems: 'center', 
              gap: 2, 
              flexWrap: 'wrap',
              position: 'sticky',
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
                {type === 'test_plan' && lastGeneratedCode && (
                  <Tooltip 
                    title="Используется последний сгенерированный код для анализа"
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
                position: 'sticky',
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
                onChange={(e) => setDarkTheme(e.target.checked)}
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
  } = props;

  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} fullWidth maxWidth="sm">
      <DialogTitle>Анализ исторических багов GitLab</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
        <TextField
          label="Repo ID или namespace/project"
          value={repoId}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setRepoId(e.target.value)}
          placeholder="123456 или group/project"
          required
          fullWidth
        />
        <TextField
          label="Метки (через запятую)"
          value={labels}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setLabels(e.target.value)}
          placeholder="bug,defect,Bug"
          helperText="Если пусто — используется 'bug'"
          fullWidth
        />
        <FormControl fullWidth>
          <InputLabel id="defects-state-label">State</InputLabel>
          <Select
            labelId="defects-state-label"
            value={state}
            label="State"
            onChange={(e: SelectChangeEvent) => setState(e.target.value as 'all' | 'opened' | 'closed')}
          >
            <MenuItem value="all">all</MenuItem>
            <MenuItem value="opened">opened</MenuItem>
            <MenuItem value="closed">closed</MenuItem>
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} disabled={loading} color="inherit">
          Отмена
        </Button>
        <Button
          variant="contained"
          onClick={onSubmit}
          disabled={loading || !repoId.trim()}
          sx={{ bgcolor: '#00ff9d', color: '#0b1220', fontWeight: 'bold' }}
        >
          {loading ? <CircularProgress size={20} sx={{ color: '#0b1220' }} /> : 'Анализировать'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}