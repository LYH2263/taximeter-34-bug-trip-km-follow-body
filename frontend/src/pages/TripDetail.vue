<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, patchJSON, postJSON } from '../api'
const route = useRoute()
const trip = ref(null)
const fare = ref(null)          // 只读拆解（persist=false，run_id 为空）
const savedRun = ref(null)      // 已落表回包（历史快照，改公里后仍是旧值）
const editKm = ref(null)
const msg = ref('')
const notFound = ref(false)

const preview = async () => {
  fare.value = await postJSON('/api/fare', {
    distance_km: trip.value.distance_km, slow_min: trip.value.slow_min,
    night: !!trip.value.night, trip_id: trip.value.id, persist: false,
  })
}
const load = async () => {
  savedRun.value = null; msg.value = ''; notFound.value = false
  try {
    trip.value = await getJSON(`/api/trips/${route.params.id}`)
  } catch { notFound.value = true; trip.value = null; return }
  editKm.value = trip.value.distance_km
  await preview()
}
const saveKm = async () => {
  trip.value = await patchJSON(`/api/trips/${trip.value.id}`, { distance_km: Number(editKm.value) })
  await preview()  // 只读拆解跟新值；savedRun 保持旧拆解旧输入
  msg.value = '公里已写回行程'
}
const saveRun = async () => {
  // 必须带行程编号；公里/低速/夜间以后端行程当时字段为准
  savedRun.value = await postJSON('/api/fare', {
    distance_km: trip.value.distance_km, slow_min: trip.value.slow_min,
    night: !!trip.value.night, trip_id: trip.value.id, persist: true,
  })
  msg.value = `已落表 #${savedRun.value.run_id}`
}
onMounted(load); watch(() => route.params.id, load)
</script>
<template>
  <div class="page">
    <h1 v-if="trip">{{ trip.label }}</h1>
    <p v-if="notFound">行程不存在</p>
    <template v-if="trip">
      <div class="panel">
        <h2>只读拆解</h2>
        <p class="hero-num">¥{{ fare?.total }}</p>
        <p>起步 {{ fare?.start }} · 里程 {{ fare?.mileage }} · 低速 {{ fare?.slow_fee }}</p>
        <p>输入 {{ fare?.distance_km }}km · 低速 {{ fare?.slow_min }}分 · {{ fare?.night ? '夜间' : '白天' }} · run_id {{ fare?.run_id ?? '空' }}</p>
      </div>
      <div class="panel">
        <label>行程公里 <input type="number" min="0" step="0.1" v-model.number="editKm" /></label>
        <button @click="saveKm">保存公里</button>
      </div>
      <button @click="saveRun">落表</button>
      <div class="panel" v-if="savedRun">
        <h2>已落表 #{{ savedRun.run_id }}</h2>
        <p class="hero-num">¥{{ savedRun.total }}</p>
        <p>起步 {{ savedRun.start }} · 里程 {{ savedRun.mileage }} · 低速 {{ savedRun.slow_fee }}</p>
        <p>落表输入 {{ savedRun.distance_km }}km · 低速 {{ savedRun.slow_min }}分 · {{ savedRun.night ? '夜间' : '白天' }}</p>
      </div>
      <p v-if="msg">{{ msg }}</p>
    </template>
  </div>
</template>
