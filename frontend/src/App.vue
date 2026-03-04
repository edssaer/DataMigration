<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <el-header height="60px" class="header">
      <div class="logo">数据库迁移工具</div>
      <el-menu
        :default-active="activeMenu"
        class="nav-menu"
        mode="horizontal"
        @select="handleMenuSelect"
      >
        <el-menu-item index="data-sources">
          <span>数据源管理</span>
        </el-menu-item>
        <el-menu-item index="tasks">
          <span>迁移任务</span>
        </el-menu-item>
        <el-menu-item index="settings">
          <span>基础设置</span>
        </el-menu-item>
      </el-menu>
    </el-header>

    <!-- 主内容区 -->
    <el-main class="main-content">
      <!-- 数据源管理 -->
      <div v-if="activeMenu === 'data-sources'" class="page-content">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>数据源列表</span>
              <el-button type="primary" @click="showDataSourceDialog = true">
                新增数据源
              </el-button>
            </div>
          </template>
          <el-table :data="dataSources" style="width: 100%">
            <el-table-column prop="name" label="名称" width="180" />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="host" label="主机" />
            <el-table-column prop="database" label="数据库" width="150" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="scope">
                <el-button type="primary" size="small" @click="editDataSource(scope.$index)">
                  编辑
                </el-button>
                <el-button type="danger" size="small" @click="deleteDataSource(scope.$index)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 数据源编辑对话框 -->
        <el-dialog
          v-model="showDataSourceDialog"
          :title="isEditDataSource ? '编辑数据源' : '新增数据源'"
          width="500px"
        >
          <el-form :model="dataSourceForm" label-width="80px">
            <el-form-item label="名称">
              <el-input v-model="dataSourceForm.name" placeholder="请输入数据源名称" />
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="dataSourceForm.type" placeholder="请选择数据库类型">
                <el-option label="MySQL" value="mysql" />
                <el-option label="PostgreSQL" value="postgresql" />
                <el-option label="SQL Server" value="sqlserver" />
              </el-select>
            </el-form-item>
            <el-form-item label="主机">
              <el-input v-model="dataSourceForm.host" placeholder="请输入主机地址" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number v-model="dataSourceForm.port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="dataSourceForm.user" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input type="password" v-model="dataSourceForm.password" placeholder="请输入密码" />
            </el-form-item>
            <el-form-item label="数据库">
              <el-input v-model="dataSourceForm.database" placeholder="请输入数据库名" />
            </el-form-item>
          </el-form>
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="showDataSourceDialog = false">取消</el-button>
              <el-button type="primary" @click="saveDataSource">保存</el-button>
            </span>
          </template>
        </el-dialog>
      </div>

      <!-- 迁移任务管理 -->
      <div v-if="activeMenu === 'tasks'" class="page-content">
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>迁移任务列表</span>
              <el-button type="primary" @click="showTaskDialog = true">
                新建迁移任务
              </el-button>
            </div>
          </template>
          <el-table :data="tasks" style="width: 100%">
            <el-table-column prop="name" label="任务名称" width="180" />
            <el-table-column prop="source_config.name" label="源数据源" />
            <el-table-column prop="target_config.name" label="目标数据源" />
            <el-table-column prop="target_table" label="目标表" width="150" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="scope">
                <el-button type="primary" size="small" @click="runTask(scope.row.id)">
                  执行
                </el-button>
                <el-button type="warning" size="small" @click="editTask(scope.row.id)">
                  编辑
                </el-button>
                <el-button type="danger" size="small" @click="deleteTask(scope.row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 任务编辑对话框 -->
        <el-dialog
          v-model="showTaskDialog"
          :title="isEditTask ? '编辑迁移任务' : '新建迁移任务'"
          width="800px"
        >
          <el-form :model="taskForm" label-width="100px">
            <el-form-item label="任务名称">
              <el-input v-model="taskForm.name" placeholder="请输入任务名称" />
            </el-form-item>
            
            <el-form-item label="源数据源">
              <el-select v-model="taskForm.source_config" placeholder="请选择源数据源">
                <el-option
                  v-for="source in dataSources"
                  :key="source.name"
                  :label="source.name"
                  :value="source"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="SQL查询">
              <el-input
                v-model="taskForm.source_query"
                type="textarea"
                :rows="3"
                placeholder="请输入SQL查询语句"
              />
            </el-form-item>
            
            <el-form-item label="目标数据源">
              <el-select v-model="taskForm.target_config" placeholder="请选择目标数据源">
                <el-option
                  v-for="source in dataSources"
                  :key="source.name"
                  :label="source.name"
                  :value="source"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="目标表名">
              <el-input v-model="taskForm.target_table" placeholder="请输入目标表名" />
            </el-form-item>
            
            <el-form-item label="表结构配置">
              <el-button type="primary" size="small" @click="generateTableStructure">
                生成表结构
              </el-button>
              <el-table :data="taskForm.table_structure" style="width: 100%; margin-top: 10px">
                <el-table-column prop="name" label="字段名" width="120" />
                <el-table-column prop="type" label="类型" width="100">
                  <template #default="scope">
                    <el-select v-model="scope.row.type" placeholder="请选择类型">
                      <el-option label="VARCHAR" value="VARCHAR" />
                      <el-option label="INT" value="INT" />
                      <el-option label="BIGINT" value="BIGINT" />
                      <el-option label="DATE" value="DATE" />
                      <el-option label="DATETIME" value="DATETIME" />
                      <el-option label="TEXT" value="TEXT" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column prop="length" label="长度" width="80">
                  <template #default="scope">
                    <el-input-number v-model="scope.row.length" :min="1" />
                  </template>
                </el-table-column>
                <el-table-column prop="nullable" label="允许空" width="80">
                  <template #default="scope">
                    <el-checkbox v-model="scope.row.nullable" />
                  </template>
                </el-table-column>
                <el-table-column prop="primary_key" label="主键" width="80">
                  <template #default="scope">
                    <el-checkbox v-model="scope.row.primary_key" />
                  </template>
                </el-table-column>
              </el-table>
            </el-form-item>
            
            <el-form-item label="定时设置">
              <el-select v-model="taskForm.schedule_type" placeholder="请选择定时类型">
                <el-option label="手动执行" value="manual" />
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
              </el-select>
              <el-input v-model="taskForm.schedule_time" placeholder="执行时间 (HH:MM)" style="margin-left: 10px" />
            </el-form-item>
          </el-form>
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="showTaskDialog = false">取消</el-button>
              <el-button type="primary" @click="saveTask">保存</el-button>
            </span>
          </template>
        </el-dialog>
      </div>

      <!-- 基础设置 -->
      <div v-if="activeMenu === 'settings'" class="page-content">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>基础设置</span>
            </div>
          </template>
          <el-form :model="settings" label-width="120px">
            <el-form-item label="默认字符集">
              <el-select v-model="settings.default_charset" placeholder="请选择默认字符集">
                <el-option label="utf8mb4" value="utf8mb4" />
                <el-option label="utf8" value="utf8" />
              </el-select>
            </el-form-item>
            <el-form-item label="默认存储引擎">
              <el-select v-model="settings.default_engine" placeholder="请选择默认存储引擎">
                <el-option label="InnoDB" value="InnoDB" />
                <el-option label="MyISAM" value="MyISAM" />
              </el-select>
            </el-form-item>
            <el-form-item label="批量插入大小">
              <el-input-number v-model="settings.batch_size" :min="1" :max="10000" />
            </el-form-item>
            <el-form-item label="日志级别">
              <el-select v-model="settings.log_level" placeholder="请选择日志级别">
                <el-option label="INFO" value="info" />
                <el-option label="DEBUG" value="debug" />
                <el-option label="ERROR" value="error" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveSettings">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </el-main>
  </div>
</template>

<script>
import { ElButton, ElInput, ElSelect, ElOption, ElTable, ElTableColumn, ElDialog, ElForm, ElFormItem, ElTag, ElCheckbox, ElInputNumber, ElMenu, ElMenuItem, ElHeader, ElMain, ElCard } from 'element-plus'

export default {
  name: 'App',
  components: {
    ElButton,
    ElInput,
    ElSelect,
    ElOption,
    ElTable,
    ElTableColumn,
    ElDialog,
    ElForm,
    ElFormItem,
    ElTag,
    ElCheckbox,
    ElInputNumber,
    ElMenu,
    ElMenuItem,
    ElHeader,
    ElMain,
    ElCard
  },
  data() {
    return {
      activeMenu: 'data-sources',
      dataSources: [],
      tasks: [],
      settings: {
        default_charset: 'utf8mb4',
        default_engine: 'InnoDB',
        batch_size: 1000,
        log_level: 'info'
      },
      showDataSourceDialog: false,
      isEditDataSource: false,
      editingDataSourceIndex: -1,
      dataSourceForm: {
        name: '',
        type: 'mysql',
        host: 'localhost',
        port: 3306,
        user: 'root',
        password: '@W203222w',
        database: ''
      },
      showTaskDialog: false,
      isEditTask: false,
      editingTaskId: '',
      taskForm: {
        name: '',
        source_config: {},
        source_query: '',
        target_config: {},
        target_table: '',
        table_structure: [],
        schedule_type: 'manual',
        schedule_time: '00:00'
      }
    }
  },
  mounted() {
    this.loadDataSources()
    this.loadTasks()
  },
  methods: {
    handleMenuSelect(key) {
      this.activeMenu = key
    },
    // 数据源管理
    loadDataSources() {
      this.$axios.get('/data-sources').then(response => {
        if (response.data.success) {
          this.dataSources = response.data.data
        }
      })
    },
    editDataSource(index) {
      this.isEditDataSource = true
      this.editingDataSourceIndex = index
      this.dataSourceForm = { ...this.dataSources[index] }
      this.showDataSourceDialog = true
    },
    deleteDataSource(index) {
      this.$confirm('确定要删除这个数据源吗？', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.$axios.delete(`/data-sources/${index}`).then(response => {
          if (response.data.success) {
            this.$message.success('删除成功')
            this.loadDataSources()
          } else {
            this.$message.error('删除失败')
          }
        })
      })
    },
    saveDataSource() {
      if (this.isEditDataSource) {
        this.$axios.put(`/data-sources/${this.editingDataSourceIndex}`, this.dataSourceForm).then(response => {
          if (response.data.success) {
            this.$message.success('更新成功')
            this.showDataSourceDialog = false
            this.loadDataSources()
          } else {
            this.$message.error('更新失败')
          }
        })
      } else {
        this.$axios.post('/data-sources', this.dataSourceForm).then(response => {
          if (response.data.success) {
            this.$message.success('添加成功')
            this.showDataSourceDialog = false
            this.loadDataSources()
          } else {
            this.$message.error('添加失败')
          }
        })
      }
    },
    // 迁移任务管理
    loadTasks() {
      this.$axios.get('/tasks').then(response => {
        if (response.data.success) {
          this.tasks = response.data.data
        }
      })
    },
    runTask(taskId) {
      this.$confirm('确定要执行这个迁移任务吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }).then(() => {
        this.$axios.post(`/tasks/${taskId}/run`).then(response => {
          if (response.data.success) {
            this.$message.success('任务执行成功')
            this.loadTasks()
          } else {
            this.$message.error('任务执行失败：' + response.data.message)
          }
        })
      })
    },
    editTask(taskId) {
      this.isEditTask = true
      this.editingTaskId = taskId
      this.$axios.get('/tasks').then(response => {
        if (response.data.success) {
          const task = response.data.data.find(t => t.id === taskId)
          if (task) {
            this.taskForm = { ...task }
            this.showTaskDialog = true
          }
        }
      })
    },
    deleteTask(taskId) {
      this.$confirm('确定要删除这个迁移任务吗？', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.$axios.delete(`/tasks/${taskId}`).then(response => {
          if (response.data.success) {
            this.$message.success('删除成功')
            this.loadTasks()
          } else {
            this.$message.error('删除失败')
          }
        })
      })
    },
    saveTask() {
      if (this.isEditTask) {
        this.$axios.put(`/tasks/${this.editingTaskId}`, this.taskForm).then(response => {
          if (response.data.success) {
            this.$message.success('更新成功')
            this.showTaskDialog = false
            this.loadTasks()
          } else {
            this.$message.error('更新失败')
          }
        })
      } else {
        this.$axios.post('/tasks', this.taskForm).then(response => {
          if (response.data.success) {
            this.$message.success('添加成功')
            this.showTaskDialog = false
            this.loadTasks()
          } else {
            this.$message.error('添加失败')
          }
        })
      }
    },
    generateTableStructure() {
      if (!this.taskForm.source_config || !this.taskForm.source_query) {
        this.$message.error('请选择源数据源并输入SQL查询语句')
        return
      }
      
      const source = this.taskForm.source_config
      this.$axios.post('/database/query', {
        host: source.host,
        port: source.port,
        user: source.user,
        password: source.password,
        database: source.database,
        query: this.taskForm.source_query
      }).then(response => {
        if (response.data.success && response.data.result.length > 0) {
          const columns = Object.keys(response.data.result[0])
          this.taskForm.table_structure = columns.map(column => ({
            name: column,
            type: 'VARCHAR',
            length: 255,
            nullable: true,
            primary_key: false
          }))
          this.$message.success('表结构生成成功')
        } else {
          this.$message.error('查询结果为空，无法生成表结构')
        }
      })
    },
    getStatusType(status) {
      switch (status) {
        case 'running':
          return 'warning'
        case 'completed':
          return 'success'
        case 'failed':
          return 'danger'
        default:
          return 'info'
      }
    },
    // 基础设置
    saveSettings() {
      // 这里可以保存设置到后端
      this.$message.success('设置保存成功')
    }
  }
}
</script>

<style>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.logo {
  font-size: 20px;
  font-weight: bold;
}

.nav-menu {
  background-color: transparent;
  border-bottom: none;
}

.nav-menu .el-menu-item {
  color: white;
}

.nav-menu .el-menu-item.is-active {
  color: white;
  background-color: rgba(255, 255, 255, 0.2);
}

.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f5f7fa;
}

.page-content {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mb-4 {
  margin-bottom: 20px;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
}
</style>