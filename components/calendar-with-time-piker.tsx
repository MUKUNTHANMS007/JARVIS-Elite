"use client"

import * as React from "react"
import { Clock2Icon } from "lucide-react"

import { Calendar } from "@/components/ui/calendar-rac"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CalendarDate, getLocalTimeZone, fromDate } from "@internationalized/date"

export interface DateTimePickerProps {
  date: Date | undefined;
  setDate: (date: Date | undefined) => void;
  startTime: string;
  setStartTime: (time: string) => void;
  endTime: string;
  setEndTime: (time: string) => void;
}

export function DateTimePicker({
  date,
  setDate,
  startTime,
  setStartTime,
  endTime,
  setEndTime
}: DateTimePickerProps) {
  return (
    <Card className="w-full py-4 border-none shadow-none bg-zinc-50 rounded-3xl">
      <CardContent className="px-4">
        <Calendar
          aria-label="Event Date"
          value={date ? fromDate(date, getLocalTimeZone()) : undefined}
          onChange={(newDate) => {
            if (newDate) {
              setDate(newDate.toDate(getLocalTimeZone()));
            }
          }}
          className="bg-transparent p-0 mx-auto"
        />
      </CardContent>
      <CardFooter className="flex flex-col gap-6 border-t border-black/5 px-4 !pt-6">
        <div className="flex w-full flex-col gap-3">
          <Label htmlFor="time-from" className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 ml-2">Start Time</Label>
          <div className="relative flex w-full items-center gap-2">
            <Clock2Icon className="text-zinc-400 pointer-events-none absolute left-3 size-4 select-none" />
            <Input
              id="time-from"
              type="time"
              step="1"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="bg-white border-none rounded-2xl pl-10 pr-4 py-3 text-black font-medium focus:ring-2 focus:ring-black h-12"
            />
          </div>
        </div>
        <div className="flex w-full flex-col gap-3">
          <Label htmlFor="time-to" className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 ml-2">End Time (Optional)</Label>
          <div className="relative flex w-full items-center gap-2">
            <Clock2Icon className="text-zinc-400 pointer-events-none absolute left-3 size-4 select-none" />
            <Input
              id="time-to"
              type="time"
              step="1"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="bg-white border-none rounded-2xl pl-10 pr-4 py-3 text-black font-medium focus:ring-2 focus:ring-black h-12"
            />
          </div>
        </div>
      </CardFooter>
    </Card>
  )
}
