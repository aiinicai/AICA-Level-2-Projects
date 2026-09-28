// Sign-in screen
import { post, showError } from '../store.js';
import { AppIcon } from '../components.js';

const { ref } = Vue;

export const LoginPage = {
  components: { AppIcon },
  emits: ['signed-in'],
  setup(props, { emit }) {
    const username = ref('');
    const password = ref('');
    const busy = ref(false);
    const error = ref('');
    async function submit() {
      error.value = '';
      busy.value = true;
      try {
        await post('/api/auth/login', { username: username.value, password: password.value });
        emit('signed-in');
      } catch (e) {
        error.value = e.message || 'Sign-in failed';
      } finally {
        busy.value = false;
      }
    }
    return { username, password, busy, error, submit };
  },
  template: `
  <div class="login-bg">
    <form class="login-card" @submit.prevent="submit" autocomplete="on">
      <div class="row" style="gap:12px;margin-bottom:18px">
        <div class="brand-mark">116</div>
        <div><div style="font-size:18px;font-weight:700">Lease116</div><div class="small muted">Ind AS 116 · IFRS 16 lease accounting</div></div>
      </div>
      <div class="col" style="gap:12px">
        <label class="field">Username<input v-model="username" autocomplete="username" autofocus required></label>
        <label class="field">Password<input v-model="password" type="password" autocomplete="current-password" required></label>
        <div v-if="error" class="alert bad"><AppIcon name="circle-x"/><div>{{ error }}</div></div>
        <button class="btn primary" style="height:38px;justify-content:center" :disabled="busy">
          <AppIcon :name="busy ? 'refresh-cw' : 'lock-open'" :cls="busy ? 'spin' : ''"/> Sign in
        </button>
      </div>
      <div class="small muted" style="margin-top:16px;line-height:1.5">
        Runs locally on this computer — agreements and calculations stay on this machine unless you explicitly send a document to a cloud AI service.
      </div>
    </form>
  </div>`,
};
