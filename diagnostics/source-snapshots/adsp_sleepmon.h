/*
 * Copyright (c) Qualcomm Technologies, Inc.
 *
 * UAPI definitions for the ADSP sleep monitor driver.
 *
 * This header is reconstructed for the MEIZU 20 (m2381) device tree build:
 * the original vendor kernel source is not public, so only the symbols
 * actually consumed by the QTI audio PAL are provided here.
 */

#ifndef _UAPI_MISC_ADSPSLEEPMON_H
#define _UAPI_MISC_ADSPSLEEPMON_H

#include <linux/types.h>
#include <linux/ioctl.h>

/* Character device exposed by the sleep monitor driver */
#define ADSPSLEEPMON_DEVICE_NAME "/dev/adspsleepmon"

/* ioctl version negotiated with the driver */
#define ADSPSLEEPMON_IOCTL_VER_1		0x00000001

/* Client register / deregister */
#define ADSPSLEEPMON_IOCTL_REGISTER		_IOW('a', 1, struct adspsleepmon_ioctl)
#define ADSPSLEEPMON_IOCTL_DEREGISTER		_IOW('a', 2, struct adspsleepmon_ioctl)

/* Audio activity notification */
#define ADSPSLEEPMON_IOCTL_AUDIO_ACTIVITY	_IOW('a', 3, struct adspsleepmon_ioctl_audio)

/* Audio activity commands carried in adspsleepmon_ioctl_audio.command */
#define ADSPSLEEPMON_AUDIO_ACTIVITY_START	0x00000000
#define ADSPSLEEPMON_AUDIO_ACTIVITY_STOP	0x00000001
#define ADSPSLEEPMON_AUDIO_ACTIVITY_LPI_START	0x00000002
#define ADSPSLEEPMON_AUDIO_ACTIVITY_LPI_STOP	0x00000003

#define ADSPSLEEPMON_IOCTL_AUDIO_VER_1		0x00000001
#define ADSPSLEEPMON_IOCTL_AUDIO_VER_MAX	ADSPSLEEPMON_IOCTL_AUDIO_VER_1

/* Generic client request */
struct adspsleepmon_ioctl {
	__u32 version;
	__u32 command;
	__u32 timeout_ms;
	__s32 status;
};

/* Audio activity notification payload */
struct adspsleepmon_ioctl_audio {
	__u32 version;
	__u32 command;
	__s32 status;
};

#endif /* _UAPI_MISC_ADSPSLEEPMON_H */
