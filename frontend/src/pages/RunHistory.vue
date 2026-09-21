<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
onMounted(async () => { items.value = (await getJSON('/api/history')).items })
</script>
<template>
  <div class="page"><h1>记录</h1>
    <table>
      <tr v-for="h in items" :key="h.id">
        <td>#{{ h.id }}</td>
        <td>{{ h.kind }}</td>
        <td>{{ h.input?.distance_km }}km · 低速{{ h.input?.slow_min }}分</td>
        <td>¥{{ h.result?.total }}</td>
        <td>
          <router-link v-if="h.trip_id" :to="`/trips/${h.trip_id}`" class="trip-tag">
            行程 #{{ h.trip_id }}{{ h.trip_label ? ' ' + h.trip_label : '' }}
          </router-link>
          <span v-else class="muted-tag">无行程</span>
        </td>
      </tr>
    </table>
  </div>
</template>
