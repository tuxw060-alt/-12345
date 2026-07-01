import { useState } from 'react'
import { Button, Input, message } from 'antd'
import {
  BarChartOutlined,
  BranchesOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  DownloadOutlined,
  FileTextOutlined,
  LockOutlined,
  PlayCircleOutlined,
  SafetyCertificateOutlined,
  ScanOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import axios from 'axios'

interface Props {
  onLogin: (token: string) => void
}

const modules = [
  { icon: <ScanOutlined />, title: '发票 OCR 与结构化', desc: '识别票面关键信息，按客户归档，减少重复录入。' },
  { icon: <FileTextOutlined />, title: '凭证审核', desc: '摘要、科目、借贷方向和金额集中复核。' },
  { icon: <TeamOutlined />, title: '客户管理', desc: '维护企业、税号、联系人和纳税人类型。' },
  { icon: <BranchesOutlined />, title: '科目规则', desc: '用关键词和优先级沉淀团队记账经验。' },
  { icon: <DownloadOutlined />, title: '金蝶导出', desc: '生成可导入金蝶快记帐的凭证 Excel。' },
  { icon: <BarChartOutlined />, title: '财务报表', desc: '按客户和期间生成余额表、利润表。' },
]

export default function Login({ onLogin }: Props) {
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (!password) {
      message.warning('请输入登录密码')
      return
    }
    setLoading(true)
    try {
      const res = await axios.post('/api/v1/auth/login', { password })
      const token = res.data.token
      localStorage.setItem('token', token)
      onLogin(token)
      message.success('登录成功')
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登录失败'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <header className="login-header">
        <div className="login-brand">
          <span className="login-brand-mark">快</span>
          <span>
            <strong>快记帐</strong>
            <small>AI Accounting Copilot</small>
          </span>
        </div>
        <a href="#login" className="login-header-action">
          进入工作台
        </a>
      </header>

      <section className="login-hero">
        <div className="login-copy">
          <p className="login-eyebrow">为代理记账机构设计的 AI 工作台</p>
          <h1>从发票到凭证，让每个客户的账更快、更稳、更可追溯。</h1>
          <p className="login-lede">
            快记帐把票据识别、科目匹配、凭证审核、金蝶导出和报表生成串成一条清晰流程，
            帮团队减少重复录入，把时间留给复核和客户服务。
          </p>

          <div className="login-actions">
            <a href="#login" className="login-primary-link">
              <CalendarOutlined />
              登录系统
            </a>
            <a href="#workflow" className="login-secondary-link">
              <PlayCircleOutlined />
              查看流程
            </a>
          </div>

          <div className="login-metrics">
            <span>
              <strong>6</strong>
              核心模块
            </span>
            <span>
              <strong>3</strong>
              步生成凭证
            </span>
            <span>
              <strong>Excel</strong>
              直导金蝶
            </span>
          </div>
        </div>

        <div className="login-preview" aria-label="快记帐工作台预览">
          <div className="preview-window-bar">
            <span />
            <span />
            <span />
            <strong>凭证生成中心</strong>
          </div>
          <div className="preview-window-body">
            <aside>
              <b>快记帐</b>
              <button className="active">
                <ScanOutlined />
                发票识别
              </button>
              <button>
                <FileTextOutlined />
                凭证审核
              </button>
              <button>
                <TeamOutlined />
                客户管理
              </button>
              <button>
                <DownloadOutlined />
                金蝶导出
              </button>
            </aside>
            <div className="preview-workspace">
              <div className="preview-client">
                <span>当前客户</span>
                <strong>上海云舟科技有限公司</strong>
                <em>借贷已平衡</em>
              </div>
              <div className="preview-invoice">
                <div className="preview-invoice-icon">
                  <CloudUploadOutlined />
                </div>
                <div>
                  <span>增值税电子普通发票</span>
                  <strong>云服务费 3,860.00</strong>
                </div>
                <b>96%</b>
              </div>
              <div className="preview-voucher">
                <div className="preview-voucher-head">
                  <strong>推荐凭证</strong>
                  <span>记-024</span>
                </div>
                <p>
                  <span>6602.03 云服务费</span>
                  <b className="debit">借 3,860.00</b>
                </p>
                <p>
                  <span>2221.01 进项税额</span>
                  <b className="debit">借 218.49</b>
                </p>
                <p>
                  <span>1002 银行存款</span>
                  <b className="credit">贷 4,078.49</b>
                </p>
              </div>
              <div className="preview-stats">
                <span>
                  <small>待复核票据</small>
                  <strong>18</strong>
                </span>
                <span>
                  <small>已确认凭证</small>
                  <strong>126</strong>
                </span>
                <span>
                  <small>规则命中率</small>
                  <strong>91%</strong>
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="workflow" className="login-workflow">
        <article>
          <span>01</span>
          <CloudUploadOutlined />
          <h2>上传发票</h2>
          <p>集中上传客户票据，自动提取抬头、金额、税额和摘要。</p>
        </article>
        <article>
          <span>02</span>
          <BranchesOutlined />
          <h2>AI 匹配科目</h2>
          <p>结合关键词规则和历史习惯，生成借贷分录。</p>
        </article>
        <article>
          <span>03</span>
          <SafetyCertificateOutlined />
          <h2>人工复核</h2>
          <p>低置信度字段、借贷差额和导出状态清晰呈现。</p>
        </article>
        <article>
          <span>04</span>
          <DownloadOutlined />
          <h2>导出金蝶</h2>
          <p>按客户和期间生成可导入金蝶快记帐的 Excel。</p>
        </article>
      </section>

      <section className="login-lower">
        <div className="login-module-grid">
          {modules.map((item) => (
            <article key={item.title}>
              {item.icon}
              <h2>{item.title}</h2>
              <p>{item.desc}</p>
            </article>
          ))}
        </div>

        <section id="login" className="login-card">
          <div className="login-card-icon">
            <CheckCircleOutlined />
          </div>
          <h2>进入快记帐工作台</h2>
          <p>请输入访问密码，继续处理客户票据、凭证和报表。</p>
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="请输入登录密码"
            size="large"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onPressEnter={handleLogin}
          />
          <Button type="primary" size="large" block loading={loading} onClick={handleLogin}>
            登录
          </Button>
        </section>
      </section>
    </main>
  )
}
